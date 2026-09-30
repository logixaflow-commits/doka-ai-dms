"""
Office DMS - Reminder Routes
CRUD for reminders, dismiss, and manual generation triggers.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import require_staff, require_admin, get_client_info
from app.core.logging import get_logger, log_audit
from app.models.database import Reminder, Document
from app.models.schemas import ReminderCreate, ReminderUpdate, ReminderDismissRequest

logger = get_logger(__name__)
router = APIRouter()


def _reminder_to_dict(r: Reminder) -> dict:
    return {
        "id": r.id,
        "document_id": r.document_id,
        "document_filename": r.document.original_filename if r.document else None,
        "reminder_type": r.reminder_type,
        "message": r.message,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "is_dismissed": r.is_dismissed,
        "dismissed_at": r.dismissed_at.isoformat() if r.dismissed_at else None,
        "priority": r.priority,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("")
async def list_reminders(
    type: Optional[str] = None,
    dismissed: Optional[bool] = None,
    priority: Optional[str] = None,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """List reminders with optional filters."""
    query = db.query(Reminder)

    if type:
        query = query.filter(Reminder.reminder_type == type)
    if dismissed is not None:
        query = query.filter(Reminder.is_dismissed == dismissed)
    if priority:
        query = query.filter(Reminder.priority == priority)

    reminders = query.order_by(desc(Reminder.created_at)).all()
    return [_reminder_to_dict(r) for r in reminders]


@router.get("/upcoming")
async def get_upcoming_reminders(
    days: int = 7,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get upcoming reminders within N days."""
    from datetime import timedelta

    cutoff = datetime.utcnow() + timedelta(days=days)
    reminders = (
        db.query(Reminder)
        .filter(
            Reminder.due_date <= cutoff,
            Reminder.is_dismissed == False,
        )
        .order_by(Reminder.due_date)
        .all()
    )

    return [_reminder_to_dict(r) for r in reminders]


@router.post("")
async def create_reminder(
    request: Request,
    reminder_data: ReminderCreate,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Create a new reminder."""
    if reminder_data.document_id:
        doc = (
            db.query(Document).filter(Document.id == reminder_data.document_id).first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

    reminder = Reminder(
        document_id=reminder_data.document_id,
        reminder_type=reminder_data.reminder_type.value,
        message=reminder_data.message,
        due_date=reminder_data.due_date,
        priority=reminder_data.priority,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    log_audit(
        "REMINDER_CREATED",
        current_user.id,
        {
            "reminder_id": reminder.id,
            "document_id": reminder_data.document_id,
            "type": reminder_data.reminder_type.value,
        },
    )

    return _reminder_to_dict(reminder)


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: int,
    update_data: ReminderUpdate,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Update a reminder."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if update_data.message:
        reminder.message = update_data.message
    if update_data.due_date:
        reminder.due_date = update_data.due_date
    if update_data.priority:
        reminder.priority = update_data.priority

    db.commit()
    return _reminder_to_dict(reminder)


@router.post("/{reminder_id}/dismiss")
async def dismiss_reminder(
    request: Request,
    reminder_id: int,
    dismiss_data: ReminderDismissRequest = None,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Dismiss a reminder."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.is_dismissed:
        return _reminder_to_dict(reminder)

    reminder.is_dismissed = True
    reminder.dismissed_at = datetime.utcnow()
    reminder.dismissed_by = current_user.id

    db.commit()

    log_audit(
        "REMINDER_DISMISSED",
        current_user.id,
        {
            "reminder_id": reminder_id,
            "document_id": reminder.document_id,
        },
    )

    return _reminder_to_dict(reminder)


@router.post("/{reminder_id}/reactivate")
async def reactivate_reminder(
    request: Request,
    reminder_id: int,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Reactivate a dismissed reminder."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.is_dismissed = False
    reminder.dismissed_at = None
    reminder.dismissed_by = None

    db.commit()
    return _reminder_to_dict(reminder)


@router.delete("/{reminder_id}")
async def delete_reminder(
    request: Request,
    reminder_id: int,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Delete a reminder."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(reminder)
    db.commit()
    return {"message": "Reminder deleted"}


@router.post("/generate")
async def generate_reminders(
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually trigger reminder generation (admin only)."""
    from app.core.tasks import check_eta_reminders, check_overdue_sops

    eta_result = check_eta_reminders.delay()
    sop_result = check_overdue_sops.delay()

    log_audit("REMINDERS_GENERATED", current_user.id, {})

    return {
        "message": "Reminder generation triggered",
        "tasks": [eta_result.id, sop_result.id],
    }
