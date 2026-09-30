"""
Office DMS - SOP Routes
SOP template management and instance tracking with progress.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.core.security import (
    require_staff,
    require_admin,
    get_client_info,
    can_approve_document,
)
from app.core.logging import get_logger, log_audit
from app.models.database import SOPTemplate, SOPInstance, Document
from app.models.schemas import (
    SOPTemplateCreate,
    SOPTemplateUpdate,
    SOPTemplateResponse,
    SOPInstanceCreate,
    SOPInstanceUpdate,
    SOPInstanceAdvanceRequest,
    SOPInstanceResponse,
)

logger = get_logger(__name__)
router = APIRouter()


def _instance_to_response(inst: SOPInstance) -> dict:
    """Convert SOPInstance to response dict."""
    return {
        "id": inst.id,
        "template_id": inst.template_id,
        "template_name": inst.template.name if inst.template else "Unknown",
        "document_id": inst.document_id,
        "document_filename": inst.document.original_filename if inst.document else None,
        "current_step_index": inst.current_step_index,
        "current_step": inst.current_step,
        "progress_percentage": inst.progress_percentage,
        "status": inst.status,
        "due_date": inst.due_date.isoformat() if inst.due_date else None,
        "completed_at": inst.completed_at.isoformat() if inst.completed_at else None,
        "notes": inst.notes,
        "step_history": inst.step_history,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
    }


# =============================================================================
# SOP Templates
# =============================================================================
@router.get("/templates")
async def list_templates(
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """List all SOP templates."""
    templates = db.query(SOPTemplate).filter(SOPTemplate.is_active == True).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "document_types": t.document_types,
            "steps_count": len(t.steps) if t.steps else 0,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in templates
    ]


@router.post("/templates")
async def create_template(
    request: Request,
    template_data: SOPTemplateCreate,
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new SOP template (admin only)."""
    template = SOPTemplate(
        name=template_data.name,
        description=template_data.description,
        document_types=template_data.document_types,
        steps=[step.model_dump() for step in template_data.steps],
        is_active=template_data.is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    log_audit(
        "SOP_TEMPLATE_CREATED",
        admin_user.id,
        {"template_id": template.id, "name": template.name},
    )
    return {"id": template.id, "message": "SOP template created"}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get SOP template details."""
    template = db.query(SOPTemplate).filter(SOPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "document_types": template.document_types,
        "steps": template.steps,
        "is_active": template.is_active,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }


@router.put("/templates/{template_id}")
async def update_template(
    request: Request,
    template_id: int,
    template_data: SOPTemplateUpdate,
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update SOP template (admin only)."""
    template = db.query(SOPTemplate).filter(SOPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template_data.name:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.document_types is not None:
        template.document_types = template_data.document_types
    if template_data.steps:
        template.steps = [step.model_dump() for step in template_data.steps]
    if template_data.is_active is not None:
        template.is_active = template_data.is_active

    db.commit()
    log_audit("SOP_TEMPLATE_UPDATED", admin_user.id, {"template_id": template_id})
    return {"message": "SOP template updated"}


@router.delete("/templates/{template_id}")
async def delete_template(
    request: Request,
    template_id: int,
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete SOP template (admin only)."""
    template = db.query(SOPTemplate).filter(SOPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    log_audit("SOP_TEMPLATE_DELETED", admin_user.id, {"template_id": template_id})
    return {"message": "SOP template deleted"}


# =============================================================================
# SOP Instances
# =============================================================================
@router.get("/instances")
async def list_instances(
    status: str = None,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """List all SOP instances with optional status filter."""
    query = db.query(SOPInstance)
    if status:
        query = query.filter(SOPInstance.status == status)

    instances = query.order_by(desc(SOPInstance.created_at)).all()
    return [_instance_to_response(inst) for inst in instances]


@router.post("/instances")
async def create_instance(
    request: Request,
    instance_data: SOPInstanceCreate,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Create a new SOP instance from a template."""
    template = (
        db.query(SOPTemplate)
        .filter(SOPTemplate.id == instance_data.template_id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Calculate due date from template step durations
    total_days = sum(step.get("duration_days", 1) for step in template.steps)
    due_date = instance_data.due_date or (
        datetime.utcnow() + timedelta(days=total_days)
    )

    instance = SOPInstance(
        template_id=instance_data.template_id,
        document_id=instance_data.document_id,
        status="not_started",
        due_date=due_date,
        notes=instance_data.notes,
        current_step_index=0,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    log_audit(
        "SOP_INSTANCE_CREATED",
        current_user.id,
        {
            "instance_id": instance.id,
            "template_id": template.id,
            "document_id": instance_data.document_id,
        },
    )

    return _instance_to_response(instance)


@router.get("/instances/{instance_id}")
async def get_instance(
    instance_id: int,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get SOP instance details."""
    instance = db.query(SOPInstance).filter(SOPInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="SOP instance not found")
    return _instance_to_response(instance)


@router.post("/instances/{instance_id}/start")
async def start_instance(
    request: Request,
    instance_id: int,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Start an SOP instance (move from not_started to in_progress)."""
    instance = db.query(SOPInstance).filter(SOPInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="SOP instance not found")

    if instance.status != "not_started":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start instance with status: {instance.status}",
        )

    instance.status = "in_progress"
    instance.updated_at = datetime.utcnow()
    db.commit()

    log_audit("SOP_STARTED", current_user.id, {"instance_id": instance_id})
    return _instance_to_response(instance)


@router.post("/instances/{instance_id}/advance")
async def advance_instance(
    request: Request,
    instance_id: int,
    advance_data: SOPInstanceAdvanceRequest,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Advance SOP to next step."""
    instance = db.query(SOPInstance).filter(SOPInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="SOP instance not found")

    if instance.status not in ["in_progress", "not_started"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance instance with status: {instance.status}",
        )

    template = instance.template
    if not template or not template.steps:
        raise HTTPException(status_code=400, detail="No steps defined in template")

    current_step = instance.current_step
    if not current_step:
        raise HTTPException(status_code=400, detail="No current step to advance from")

    # Record step completion in history
    history = instance.step_history or []
    history.append(
        {
            "step_index": instance.current_step_index,
            "step_name": current_step.get("name", "Unknown"),
            "status": advance_data.step_status,
            "completed_at": datetime.utcnow().isoformat(),
            "completed_by": current_user.id,
            "notes": advance_data.notes,
        }
    )
    instance.step_history = history

    # Advance to next step
    instance.current_step_index += 1

    # Check if all steps completed
    if instance.current_step_index >= len(template.steps):
        instance.status = "completed"
        instance.completed_at = datetime.utcnow()
    else:
        instance.status = "in_progress"

    instance.updated_at = datetime.utcnow()
    db.commit()

    log_audit(
        "SOP_ADVANCED",
        current_user.id,
        {
            "instance_id": instance_id,
            "step_index": instance.current_step_index,
            "step_status": advance_data.step_status,
        },
    )

    return _instance_to_response(instance)


@router.put("/instances/{instance_id}")
async def update_instance(
    request: Request,
    instance_id: int,
    update_data: SOPInstanceUpdate,
    current_user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Update SOP instance."""
    instance = db.query(SOPInstance).filter(SOPInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="SOP instance not found")

    if update_data.status:
        instance.status = update_data.status.value
    if update_data.notes is not None:
        instance.notes = update_data.notes
    if update_data.due_date:
        instance.due_date = update_data.due_date

    instance.updated_at = datetime.utcnow()
    db.commit()

    return _instance_to_response(instance)
