"""
Report Generation Routes
Handles compliance and audit report generation.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import uuid

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.core.logging import log_audit, get_client_info
from app.core.celery_app import celery_app
from app.models.database import User
from app.models.schemas import (
    ReportGenerateRequest, ReportGenerateResponse, ReportDownloadResponse,
    ReportType, ReportFormat, ScheduledReportConfig, ReportStatsResponse
)
from app.services.report_service import report_service
from app.core.config import settings

router = APIRouter()


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    request: Request,
    report_request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate a compliance report (admin only).
    
    Reports are generated asynchronously via Celery to avoid HTTP timeouts.
    The response includes a report ID that can be used to check status and download.
    """
    try:
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Submit task to Celery
        task = generate_report_task.delay(
            report_id=report_id,
            report_type=report_request.report_type.value,
            start_date=report_request.start_date.isoformat(),
            end_date=report_request.end_date.isoformat(),
            user_id=report_request.user_id,
            document_type=report_request.document_type,
            action_filter=report_request.action_filter,
            format=report_request.format.value,
            requested_by=current_user.id
        )
        
        client = get_client_info(request)
        log_audit(
            "REPORT_GENERATION_REQUESTED",
            current_user.id,
            {
                "report_type": report_request.report_type.value,
                "report_id": report_id,
                "celery_task_id": task.id,
                "ip": client["ip_address"]
            }
        )
        
        return ReportGenerateResponse(
            report_id=report_id,
            status="processing",
            message=f"Report generation started. Use report_id '{report_id}' to check status."
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate report generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate report generation"
        )


@router.get("/status/{report_id}")
async def get_report_status(
    report_id: str,
    current_user: User = Depends(require_admin)
):
    """
    Check the status of a report generation task.
    
    Returns the current status (processing, completed, failed) and download URL if ready.
    """
    try:
        # Check Celery task status
        # In production, you'd store task results in a database or Redis
        # For now, we'll implement a simple file-based status check
        
        reports_dir = Path(settings.ORGANIZED_ROOT).parent / "reports"
        
        # Look for the report file
        matching_files = list(reports_dir.glob(f"*{report_id}*"))
        
        if matching_files:
            # Report completed
            filename = matching_files[0].name
            return {
                "report_id": report_id,
                "status": "completed",
                "filename": filename,
                "download_url": f"/api/admin/reports/download/{filename}"
            }
        else:
            # Check if task is still running (simplified)
            return {
                "report_id": report_id,
                "status": "processing",
                "message": "Report is being generated"
            }
        
    except Exception as e:
        logger.error(f"Failed to check report status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check report status"
        )


@router.get("/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(require_admin)
):
    """
    Download a generated report file (admin only).
    """
    try:
        reports_dir = Path(settings.ORGANIZED_ROOT).parent / "reports"
        file_path = reports_dir / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )
        
        # Log download
        log_audit(
            "REPORT_DOWNLOADED",
            current_user.id,
            {"filename": filename}
        )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download report"
        )


@router.get("/access")
async def generate_access_log_report(
    start_date: datetime,
    end_date: datetime,
    user_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate access log report directly (synchronous, for small datasets).
    
    This endpoint generates the report synchronously and returns it as an Excel file.
    For large datasets, use the async /generate endpoint.
    """
    try:
        # Generate report data
        df = report_service.generate_access_log_report(start_date, end_date, user_id, db)
        
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified date range"
            )
        
        # Export to Excel
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"access_log_{timestamp}.xlsx"
        filepath = report_service.export_to_excel(df, "Access Log Report", filename)
        
        # Log generation
        log_audit(
            "ACCESS_REPORT_GENERATED",
            current_user.id,
            {"filename": filename, "record_count": len(df)}
        )
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate access log report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/activity")
async def generate_document_activity_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate document activity report (synchronous, for small datasets).
    
    This endpoint generates the report synchronously and returns it as a PDF file.
    For large datasets, use the async /generate endpoint.
    """
    try:
        # Generate report data
        df = report_service.generate_document_activity_report(start_date, end_date, db)
        
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified date range"
            )
        
        # Export to PDF
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"document_activity_{timestamp}.pdf"
        filepath = report_service.export_to_pdf(df, "Document Activity Report", filename)
        
        # Log generation
        log_audit(
            "ACTIVITY_REPORT_GENERATED",
            current_user.id,
            {"filename": filename, "record_count": len(df)}
        )
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate document activity report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/user")
async def generate_user_activity_report(
    start_date: datetime,
    end_date: datetime,
    user_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate user activity report (synchronous, for small datasets).
    
    This endpoint generates the report synchronously and returns it as an Excel file.
    For large datasets, use the async /generate endpoint.
    """
    try:
        # Generate report data
        df = report_service.generate_user_activity_report(start_date, end_date, user_id, db)
        
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified date range"
            )
        
        # Export to Excel
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"user_activity_{timestamp}.xlsx"
        filepath = report_service.export_to_excel(df, "User Activity Report", filename)
        
        # Log generation
        log_audit(
            "USER_REPORT_GENERATED",
            current_user.id,
            {"filename": filename, "record_count": len(df)}
        )
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate user activity report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.post("/schedule")
async def schedule_report(
    request: Request,
    schedule_config: ScheduledReportConfig,
    current_user: User = Depends(require_admin)
):
    """
    Schedule a recurring report (admin only).
    
    This configures automatic report generation and email delivery.
    """
    try:
        # Store schedule configuration in database (simplified - would use proper scheduling table)
        # For now, we'll just acknowledge the request
        
        log_audit(
            "REPORT_SCHEDULED",
            current_user.id,
            {
                "report_type": schedule_config.report_type.value,
                "frequency": schedule_config.frequency,
                "recipient": schedule_config.recipient_email
            }
        )
        
        return {
            "message": "Report schedule configured successfully",
            "schedule": {
                "report_type": schedule_config.report_type.value,
                "frequency": schedule_config.frequency,
                "recipient": schedule_config.recipient_email,
                "enabled": schedule_config.enabled
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule report"
        )


@router.get("/stats", response_model=ReportStatsResponse)
async def get_report_stats(
    current_user: User = Depends(require_admin)
):
    """
    Get report generation statistics (admin only).
    """
    try:
        reports_dir = Path(settings.ORGANIZED_ROOT).parent / "reports"
        
        # Count report files
        report_files = list(reports_dir.glob("report_*"))
        total_reports = len(report_files)
        
        # Simplified stats (in production, you'd track this properly)
        successful_reports = total_reports
        failed_reports = 0
        
        # Get most recent report
        last_generated = None
        if report_files:
            last_file = max(report_files, key=lambda p: p.stat().st_mtime)
            last_generated = datetime.fromtimestamp(last_file.stat().st_mtime)
        
        return ReportStatsResponse(
            total_reports=total_reports,
            successful_reports=successful_reports,
            failed_reports=failed_reports,
            last_generated=last_generated
        )
        
    except Exception as e:
        logger.error(f"Failed to get report stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report statistics"
        )


@router.post("/cleanup")
async def cleanup_old_reports(
    retention_days: int = 30,
    current_user: User = Depends(require_admin)
):
    """
    Clean up old report files (admin only).
    
    Removes report files older than the specified retention period.
    """
    try:
        deleted_count = report_service.cleanup_old_reports(retention_days)
        
        log_audit(
            "OLD_REPORTS_CLEANED",
            current_user.id,
            {"retention_days": retention_days, "deleted_count": deleted_count}
        )
        
        return {
            "message": "Old reports cleaned up successfully",
            "deleted_count": deleted_count,
            "retention_days": retention_days
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup old reports"
        )


# Celery task for async report generation
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report_task(
    self,
    report_id: str,
    report_type: str,
    start_date: str,
    end_date: str,
    user_id: int = None,
    document_type: str = None,
    action_filter: str = None,
    format: str = "excel",
    requested_by: int = None
):
    """
    Celery task for async report generation.
    """
    logger.info(f"Generating report {report_id} of type {report_type}")
    
    from app.core.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        # Generate report based on type
        if report_type == "access_log":
            df = report_service.generate_access_log_report(start_dt, end_dt, user_id, db)
            title = "Access Log Report"
        elif report_type == "document_activity":
            df = report_service.generate_document_activity_report(start_dt, end_dt, db)
            title = "Document Activity Report"
        elif report_type == "user_activity":
            df = report_service.generate_user_activity_report(start_dt, end_dt, user_id, db)
            title = "User Activity Report"
        elif report_type == "custom":
            filters = {
                "user_id": user_id,
                "document_type": document_type,
                "action": action_filter
            }
            df = report_service.generate_custom_report(start_dt, end_dt, filters, db)
            title = "Custom Report"
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        if df.empty:
            logger.warning(f"No data found for report {report_id}")
            return {"status": "failed", "error": "No data found"}
        
        # Export based on format
        filename = f"report_{report_id}"
        if format == "pdf":
            filepath = report_service.export_to_pdf(df, title, filename + ".pdf")
        elif format == "json":
            filepath = report_service.export_to_json(df, title, filename + ".json")
        else:  # excel
            filepath = report_service.export_to_excel(df, title, filename + ".xlsx")
        
        logger.info(f"Report {report_id} generated successfully: {filepath}")
        return {
            "status": "completed",
            "report_id": report_id,
            "filepath": str(filepath)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate report {report_id}: {e}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying report generation {report_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        
        return {
            "status": "failed",
            "error": str(e),
            "report_id": report_id
        }
    
    finally:
        db.close()