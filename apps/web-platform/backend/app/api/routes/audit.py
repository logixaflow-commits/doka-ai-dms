"""
Office DMS - Audit Log Routes
View audit trail with filtering and pagination (admin only).
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import require_admin
from app.models.database import AuditLog, User

router = APIRouter()


def _filtered_audit_query(db: Session, user_id: Optional[int], document_id: Optional[int], action: Optional[str], from_date: Optional[str], to_date: Optional[str]):
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if document_id:
        query = query.filter(AuditLog.document_id == document_id)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if from_date:
        query = query.filter(AuditLog.timestamp >= from_date)
    if to_date:
        query = query.filter(AuditLog.timestamp <= to_date + " 23:59:59")
    return query


@router.get("/logs")
async def list_audit_logs(
    user_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List audit logs with filtering (admin only)."""
    query = _filtered_audit_query(db, user_id, document_id, action, from_date, to_date)

    total = query.count()
    logs = (
        query.order_by(desc(AuditLog.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else "Unknown",
                "document_id": log.document_id,
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
                "endpoint": log.endpoint,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/export")
async def export_audit_logs_csv(
    user_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Download filtered audit events as a local CSV; no third-party delivery is used."""
    logs = _filtered_audit_query(db, user_id, document_id, action, from_date, to_date).order_by(desc(AuditLog.timestamp)).limit(10000).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "username", "action", "document_id", "details", "ip_address", "endpoint"])
    for log in logs:
        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else "",
            log.user.username if log.user else "Unknown",
            log.action,
            log.document_id or "",
            log.details or "",
            log.ip_address or "",
            log.endpoint or "",
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )


@router.get("/logs/{log_id}")
async def get_audit_log(
    log_id: int,
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get specific audit log entry (admin only)."""
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.user.username if log.user else "Unknown",
        "document_id": log.document_id,
        "action": log.action,
        "details": log.details,
        "ip_address": log.ip_address,
        "endpoint": log.endpoint,
        "user_agent": log.user_agent,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


@router.get("/actions")
async def list_audit_actions(
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all distinct audit actions."""
    results = (
        db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.action)
        .all()
    )
    return {action: count for action, count in results}


@router.get("/stats")
async def get_audit_stats(
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get audit log statistics."""
    total_logs = db.query(AuditLog).count()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_logs = db.query(AuditLog).filter(AuditLog.timestamp >= today).count()

    # Top actions
    top_actions = (
        db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.action)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    return {
        "total_logs": total_logs,
        "today_logs": today_logs,
        "top_actions": [{"action": a, "count": c} for a, c in top_actions],
    }
