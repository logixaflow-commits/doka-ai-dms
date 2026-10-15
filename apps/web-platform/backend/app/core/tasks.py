"""
Office DMS - Celery Tasks
All async tasks: document processing, reminders, cleanup, backup.
"""
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.logging import get_logger
from app.core.encryption import encryption_manager
from app.core.backup_utils import postgres_dump_invocation
from app.core.storage import storage_manager
from app.core.exceptions import PipelineError
from app.services.pipeline import ProcessingPipeline
from app.services.email_service import email_service
from app.models.database import Document, Reminder, SOPInstance, AuditLog, User

logger = get_logger(__name__)


# =============================================================================
# Main Document Processing Task
# =============================================================================
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: int, file_path: str, original_filename: str, mime_type: str):
    """
    Celery task to process a document through the full AI pipeline.
    Steps: OCR -> Metadata Extraction -> Classification -> Duplicate Detection -> Storage
    """
    logger.info(f"[Task {self.request.id}] Starting processing for document {document_id}: {original_filename}")

    db = SessionLocal()
    pipeline = ProcessingPipeline(db)

    try:
        # Update document status to processing
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return {"status": "failed", "error": "Document not found"}

        doc.status = "processing"
        doc.task_id = self.request.id
        db.commit()

        # Run the full pipeline
        result = pipeline.process(
            document_id=document_id,
            file_path=file_path,
            original_filename=original_filename,
            mime_type=mime_type,
        )

        logger.info(f"[Task {self.request.id}] Processing completed for document {document_id}: {result['status']}")
        return result

    except SoftTimeLimitExceeded:
        logger.error(f"[Task {self.request.id}] Soft time limit exceeded for document {document_id}")
        _update_doc_status(db, document_id, "failed", "Processing timeout")
        db.close()
        raise

    except Exception as exc:
        logger.error(f"[Task {self.request.id}] Processing failed: {exc}")

        # Update retry count
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.retry_count = (doc.retry_count or 0) + 1
            db.commit()

        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"[Task {self.request.id}] Retrying ({self.request.retries + 1}/{self.max_retries})")
            db.close()
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            _update_doc_status(db, document_id, "failed", str(exc))
            db.close()
            return {"status": "failed", "error": str(exc), "document_id": document_id}

    finally:
        db.close()


def _update_doc_status(db: Session, doc_id: int, status: str, error_msg: str = None):
    """Helper to update document status on failure."""
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = status
            if error_msg and status == "failed":
                # Store error in extracted_metadata for visibility
                meta = doc.extracted_metadata or {}
                meta["processing_error"] = error_msg
                doc.extracted_metadata = meta
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update document status: {e}")
        db.rollback()


# =============================================================================
# Scheduled Tasks (Celery Beat)
# =============================================================================
@celery_app.task
def check_eta_reminders():
    """
    Scheduled task: Check for upcoming ETAs and generate reminders.
    Runs every 6 hours.
    """
    logger.info("Running ETA reminder check...")
    db = SessionLocal()

    try:
        warning_days = settings.notifications.get("eta_warning_days", 3)
        cutoff_date = datetime.utcnow() + timedelta(days=warning_days)

        # Find documents with ETA approaching
        docs = db.query(Document).filter(
            Document.status.in_(["completed", "approved"]),
            Document.extracted_metadata.isnot(None),
        ).all()

        reminders_created = 0
        for doc in docs:
            meta = doc.extracted_metadata or {}
            eta_str = meta.get("eta")

            if eta_str:
                try:
                    eta_date = datetime.fromisoformat(eta_str.replace("Z", "+00:00").replace("+00:00", ""))
                    if datetime.utcnow() <= eta_date <= cutoff_date:
                        # Check if reminder already exists
                        existing = db.query(Reminder).filter(
                            Reminder.document_id == doc.id,
                            Reminder.reminder_type == "eta",
                            Reminder.is_dismissed == False,
                        ).first()

                        if not existing:
                            reminder = Reminder(
                                document_id=doc.id,
                                reminder_type="eta",
                                message=f"ETA approaching for {doc.original_filename}: {eta_date.strftime('%Y-%m-%d')}",
                                due_date=eta_date,
                                priority="high" if (eta_date - datetime.utcnow()).days <= 1 else "medium",
                            )
                            db.add(reminder)
                            reminders_created += 1
                except (ValueError, TypeError):
                    continue

        db.commit()
        logger.info(f"ETA reminder check complete. Created {reminders_created} reminders.")
        return {"reminders_created": reminders_created}

    except Exception as e:
        logger.error(f"ETA reminder check failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task
def check_overdue_sops():
    """
    Scheduled task: Check for overdue SOP instances and generate reminders.
    Runs every 12 hours.
    """
    logger.info("Running overdue SOP check...")
    db = SessionLocal()

    try:
        now = datetime.utcnow()

        # Find overdue SOP instances
        overdue_sops = db.query(SOPInstance).filter(
            SOPInstance.status.in_(["not_started", "in_progress"]),
            SOPInstance.due_date.isnot(None),
            SOPInstance.due_date < now,
        ).all()

        for sop in overdue_sops:
            sop.status = "overdue"

            # Create reminder
            existing = db.query(Reminder).filter(
                Reminder.sop_instance_id == sop.id,
                Reminder.reminder_type == "overdue",
                Reminder.is_dismissed == False,
            ).first()

            if not existing:
                doc_name = sop.document.original_filename if sop.document else "N/A"
                reminder = Reminder(
                    document_id=sop.document_id,
                    sop_instance_id=sop.id,
                    reminder_type="overdue",
                    message=f"SOP '{sop.template.name}' for '{doc_name}' is overdue (due: {sop.due_date.strftime('%Y-%m-%d')})",
                    due_date=now,
                    priority="critical",
                )
                db.add(reminder)

        db.commit()
        logger.info(f"Overdue SOP check complete. {len(overdue_sops)} SOPs marked overdue.")
        return {"overdue_count": len(overdue_sops)}

    except Exception as e:
        logger.error(f"Overdue SOP check failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task
def cleanup_workspace():
    """
    Scheduled task: Clean up Processing_Workspace files older than configured max age.
    Runs daily.
    """
    logger.info("Running workspace cleanup...")

    max_age_hours = settings.cleanup.get("processing_workspace_max_age_hours", 24)
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    workspace = settings.PROCESSING_WORKSPACE

    deleted_count = 0
    freed_bytes = 0

    try:
        if not workspace.exists():
            return {"deleted": 0, "freed_mb": 0}

        for item in workspace.rglob("*"):
            if item.is_file():
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff:
                    file_size = item.stat().st_size
                    try:
                        item.unlink()
                        deleted_count += 1
                        freed_bytes += file_size
                    except Exception as e:
                        logger.warning(f"Failed to delete {item}: {e}")

        logger.info(f"Workspace cleanup complete. Deleted {deleted_count} files, freed {freed_bytes / (1024*1024):.2f} MB")
        return {"deleted": deleted_count, "freed_mb": round(freed_bytes / (1024 * 1024), 2)}

    except Exception as e:
        logger.error(f"Workspace cleanup failed: {e}")
        return {"error": str(e)}


@celery_app.task
def backup_database():
    """
    Scheduled task: Create a database backup.
    """
    logger.info("Running database backup...")

    try:
        backup_dir = settings.ORGANIZED_ROOT.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if settings.DATABASE_URL.startswith("sqlite"):
            db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
            backup_path = backup_dir / f"dms_backup_{timestamp}.db"
            shutil.copy2(str(db_path), str(backup_path))
            logger.info(f"SQLite backup created: {backup_path}")

        else:
            # Parse credentials and IPv6 hosts correctly; never interpolate a shell command.
            import subprocess
            backup_path = backup_dir / f"dms_backup_{timestamp}.sql"
            cmd, credentials = postgres_dump_invocation(
                settings.DATABASE_URL, str(backup_path)
            )
            env = os.environ.copy()
            env.update(credentials)
            subprocess.run(
                cmd, env=env, check=True, capture_output=True, text=True
            )
            logger.info(f"PostgreSQL backup created: {backup_path}")

        # Clean old backups
        retention_days = settings.BACKUP_RETENTION_DAYS
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        for backup_file in backup_dir.glob("dms_backup_*"):
            if datetime.fromtimestamp(backup_file.stat().st_ctime) < cutoff:
                backup_file.unlink(missing_ok=True)

        return {"backup_path": str(backup_path), "status": "success"}

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return {"error": str(e)}


@celery_app.task
def generate_sop_reminders():
    """
    Create reminders for SOP steps that are approaching their deadline.
    """
    logger.info("Running SOP reminder generation...")
    db = SessionLocal()

    try:
        now = datetime.utcnow()
        warning_hours = 24  # Warn 24 hours before step deadline

        active_sops = db.query(SOPInstance).filter(
            SOPInstance.status == "in_progress",
        ).all()

        reminders_created = 0
        for sop in active_sops:
            current_step = sop.current_step
            if not current_step:
                continue

            # Calculate step deadline based on SOP creation and step durations
            step_start = sop.created_at
            for i, step in enumerate(sop.template.steps):
                if i >= sop.current_step_index:
                    break
                step_start += timedelta(days=step.get("duration_days", 1))

            step_deadline = step_start + timedelta(days=current_step.get("duration_days", 1))
            warning_time = step_deadline - timedelta(hours=warning_hours)

            if now >= warning_time and now < step_deadline:
                existing = db.query(Reminder).filter(
                    Reminder.sop_instance_id == sop.id,
                    Reminder.reminder_type == "sop_deadline",
                    Reminder.is_dismissed == False,
                ).first()

                if not existing:
                    reminder = Reminder(
                        document_id=sop.document_id,
                        sop_instance_id=sop.id,
                        reminder_type="sop_deadline",
                        message=f"SOP step '{current_step.get('name')}' deadline approaching for '{sop.document.original_filename if sop.document else 'N/A'}'",
                        due_date=step_deadline,
                        priority="high",
                    )
                    db.add(reminder)
                    reminders_created += 1

        db.commit()
        logger.info(f"SOP reminder generation complete. Created {reminders_created} reminders.")
        return {"reminders_created": reminders_created}

    except Exception as e:
        logger.error(f"SOP reminder generation failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task
def check_expiry_dates_task():
    """
    Scheduled task: Check for documents expiring in 7 days and send email alerts.
    Runs daily at 8 AM.
    """
    logger.info("Running document expiry check...")
    db = SessionLocal()

    try:
        warning_days = 7
        cutoff_date = datetime.utcnow() + timedelta(days=warning_days)

        # Find documents expiring within 7 days
        expiring_docs = db.query(Document).filter(
            Document.expiry_date.isnot(None),
            Document.expiry_date <= cutoff_date,
            Document.expiry_date >= datetime.utcnow()
        ).all()

        alerts_sent = 0
        for doc in expiring_docs:
            # Get uploader info
            uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
            uploader_email = uploader.email if uploader else None
            uploader_name = uploader.username if uploader else None

            # Send email alert
            result = email_service.send_document_expiry_alert(
                document_filename=doc.original_filename,
                expiry_date=doc.expiry_date,
                expiry_notes=doc.expiry_notes,
                uploader_email=uploader_email,
                uploader_name=uploader_name
            )

            if result.get("success"):
                alerts_sent += 1
                # Also send to admin if uploader exists
                if uploader_email:
                    email_service.send_document_expiry_alert(
                        document_filename=doc.original_filename,
                        expiry_date=doc.expiry_date,
                        expiry_notes=doc.expiry_notes
                    )
            else:
                logger.warning(f"Failed to send expiry alert for document {doc.id}: {result.get('message')}")

        db.commit()
        logger.info(f"Document expiry check complete. Sent {alerts_sent} alerts.")
        return {"alerts_sent": alerts_sent, "expiring_documents": len(expiring_docs)}

    except Exception as e:
        logger.error(f"Document expiry check failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task
def send_daily_report_task():
    """
    Scheduled task: Send daily activity report at 9 AM.
    Runs daily at 9 AM.
    """
    logger.info("Running daily activity report task...")
    db = SessionLocal()

    try:
        # Get daily statistics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Get document statistics for today
        approved_today = db.query(Document).filter(
            Document.approved_at >= today,
            Document.approved_at < tomorrow,
            Document.status == 'approved'
        ).count()
        
        pending_count = db.query(Document).filter(
            Document.status == 'pending'
        ).count()
        
        total_documents = db.query(Document).count()
        
        failed_count = db.query(Document).filter(
            Document.status == 'failed'
        ).count()
        
        total_users = db.query(User).filter(User.is_active == True).count()
        
        stats = {
            'total_documents': total_documents,
            'approved_today': approved_today,
            'pending': pending_count,
            'failed': failed_count,
            'total_users': total_users
        }
        
        # Send email to admin
        result = email_service.send_daily_activity_report(
            recipient_email=settings.__dict__.get("ADMIN_EMAIL", "admin@enterprise-dms.local"),
            recipient_name="Admin",
            stats=stats
        )
        
        logger.info(f"Daily report task complete. Email sent: {result.get('success')}")
        return {"stats": stats, "email_sent": result.get("success")}
        
    except Exception as e:
        logger.error(f"Daily report task failed: {e}")
        return {"error": str(e)}
    
    finally:
        db.close()


@celery_app.task
def send_weekly_report_task():
    """
    Scheduled task: Send weekly summary report on Monday at 8 AM.
    Runs weekly on Monday at 8 AM.
    """
    logger.info("Running weekly summary report task...")
    db = SessionLocal()

    try:
        # Get weekly statistics (last 7 days)
        today = datetime.utcnow()
        week_ago = today - timedelta(days=7)
        
        # Get document statistics for this week
        approved_count = db.query(Document).filter(
            Document.approved_at >= week_ago,
            Document.approved_at < today,
            Document.status == 'approved'
        ).count()
        
        rejected_count = db.query(Document).filter(
            Document.approved_at >= week_ago,
            Document.approved_at < today,
            Document.status == 'rejected'
        ).count()
        
        total_documents = db.query(Document).filter(
            Document.created_at >= week_ago
        ).count()
        
        total_users = db.query(User).filter(User.is_active == True).count()
        
        stats = {
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'total_documents': total_documents,
            'total_users': total_users
        }
        
        # Send email to admin
        result = email_service.send_weekly_summary_report(
            recipient_email=settings.__dict__.get("ADMIN_EMAIL", "admin@enterprise-dms.local"),
            recipient_name="Admin",
            weekly_stats=stats
        )
        
        logger.info(f"Weekly report task complete. Email sent: {result.get('success')}")
        return {"stats": stats, "email_sent": result.get("success")}
        
    except Exception as e:
        logger.error(f"Weekly report task failed: {e}")
        return {"error": str(e)}
    
    finally:
        db.close()
