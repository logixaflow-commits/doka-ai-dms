"""
Office DMS - Admin Routes
System statistics, manual backup trigger, health checks, and export functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from io import StringIO
import csv
from pathlib import Path

from app.core.database import get_db
from app.core.security import require_admin, get_client_info
from app.core.logging import get_logger, log_audit
from app.core.tasks import backup_database, cleanup_workspace, check_eta_reminders
from app.core.config import settings
from app.models.database import Document, User, AuditLog, SOPInstance, Reminder
from app.models.schemas import ExportRequest, ExportResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_stats(
    admin_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get comprehensive system statistics (admin only)."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Document stats
    total_docs = db.query(Document).count()
    pending_review = db.query(Document).filter(Document.status.in_([
        "pending", "review", "unknown", "completed"
    ])).count()
    approved_today = db.query(Document).filter(
        Document.status == "approved",
        Document.approved_at >= today_start,
    ).count()
    rejected_today = db.query(Document).filter(
        Document.status == "rejected",
        Document.approved_at >= today_start,
    ).count()
    duplicates = db.query(Document).filter(Document.is_duplicate == True).count()
    suspicious = db.query(Document).filter(Document.is_suspicious == True).count()
    failed = db.query(Document).filter(Document.status == "failed").count()

    # Category distribution
    cat_results = db.query(Document.category, func.count(Document.id)).group_by(Document.category).all()
    category_distribution = {cat or "Unknown": count for cat, count in cat_results}

    # Status distribution
    status_results = db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    status_distribution = {stat: count for stat, count in status_results}

    # User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # SOP stats
    total_sops = db.query(SOPInstance).count()
    overdue_sops = db.query(SOPInstance).filter(SOPInstance.status == "overdue").count()

    # Reminder stats
    upcoming_reminders = db.query(Reminder).filter(
        Reminder.is_dismissed == False,
        Reminder.due_date >= now,
    ).count()

    return {
        "documents": {
            "total": total_docs,
            "pending_review": pending_review,
            "approved_today": approved_today,
            "rejected_today": rejected_today,
            "duplicates": duplicates,
            "suspicious": suspicious,
            "failed": failed,
            "category_distribution": category_distribution,
            "status_distribution": status_distribution,
        },
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "sops": {
            "total": total_sops,
            "overdue": overdue_sops,
        },
        "reminders": {
            "upcoming": upcoming_reminders,
        },
        "timestamp": now.isoformat(),
    }


@router.post("/backup")
async def trigger_backup(
    request: Request,
    admin_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger manual database backup (admin only)."""
    result = backup_database.delay()

    client = get_client_info(request)
    log_audit("BACKUP_TRIGGERED", admin_user.id, {"ip": client["ip_address"]})

    return {
        "message": "Backup triggered",
        "task_id": result.id,
    }


@router.post("/cleanup")
async def trigger_cleanup(
    request: Request,
    admin_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger workspace cleanup (admin only)."""
    result = cleanup_workspace.delay()

    client = get_client_info(request)
    log_audit("CLEANUP_TRIGGERED", admin_user.id, {"ip": client["ip_address"]})

    return {
        "message": "Cleanup triggered",
        "task_id": result.id,
    }


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    admin_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get recent system activity (admin only)."""
    recent_docs = db.query(Document).order_by(desc(Document.created_at)).limit(5).all()
    recent_audits = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(10).all()

    return {
        "recent_documents": [{
            "id": d.id,
            "filename": d.original_filename,
            "status": d.status,
            "category": d.category,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        } for d in recent_docs],
        "recent_audit": [{
            "id": a.id,
            "action": a.action,
            "user": a.user.username if a.user else "Unknown",
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        } for a in recent_audits],
    }


@router.get("/export")
async def export_documents(
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    category: str = None,
    format: str = "csv",
    admin_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Export documents to CSV or Excel format (admin only)."""
    query = db.query(Document)

    # Apply filters
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.filter(Document.created_at >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            query = query.filter(Document.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    if status:
        query = query.filter(Document.status == status)

    if category:
        query = query.filter(Document.category == category)

    documents = query.order_by(Document.created_at).all()

    # Log export action
    client = get_client_info(request=Request({}))
    log_audit(
        "EXPORT",
        admin_user.id,
        {
            "date_from": date_from,
            "date_to": date_to,
            "status": status,
            "category": category,
            "format": format,
            "record_count": len(documents),
            "ip": client["ip_address"],
        }
    )

    if format.lower() == "csv":
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "ID", "Original Filename", "Stored Filename", "Status",
            "Category", "Confidence", "File Size", "MIME Type",
            "Is Duplicate", "Is Suspicious", "Created At",
            "Approved At", "Uploaded By", "Approved By",
            "Rejection Reason", "Suggested Folder"
        ])

        # Write data
        for doc in documents:
            writer.writerow([
                doc.id,
                doc.original_filename,
                doc.stored_filename,
                doc.status,
                doc.category or "N/A",
                doc.confidence or 0.0,
                doc.file_size,
                doc.mime_type,
                doc.is_duplicate,
                doc.is_suspicious,
                doc.created_at.isoformat() if doc.created_at else "N/A",
                doc.approved_at.isoformat() if doc.approved_at else "N/A",
                doc.uploader.username if doc.uploader else "N/A",
                doc.approver.username if doc.approver else "N/A",
                doc.rejection_reason or "N/A",
                doc.suggested_folder or "N/A",
            ])

        output.seek(0)

        filename = f"documents_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    elif format.lower() == "xlsx":
        # For Excel, we'd need openpyxl - implementing as CSV for now
        # Could be extended to use openpyxl for true Excel export
        raise HTTPException(
            status_code=501,
            detail="Excel export not yet implemented. Use CSV format."
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'csv' or 'xlsx'."
        )
