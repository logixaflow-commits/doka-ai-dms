"""Authenticated endpoints for explicit external-AI consent lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.local_security import require_local_staff
from app.services.consent_store import PURPOSES, list_audit, list_consents, set_consent

router = APIRouter(prefix="/api/ai/consent", tags=["AI consent"])


class ConsentChange(BaseModel):
    purpose: str = Field(min_length=1, max_length=64)
    scope: str = Field(min_length=1, max_length=512)
    granted: bool


@router.get("")
async def get_my_consents(subject_id: str = Depends(require_local_staff)):
    return {"consents": list_consents(subject_id=subject_id)}


@router.put("")
async def change_my_consent(body: ConsentChange, request: Request,
                            subject_id: str = Depends(require_local_staff)):
    if body.purpose not in PURPOSES:
        raise HTTPException(status_code=422, detail="Unsupported consent purpose.")
    try:
        return set_consent(
            subject_id=subject_id,
            actor_id=subject_id,
            purpose=body.purpose,
            scope=body.scope,
            granted=body.granted,
            request_id=getattr(request.state, "request_id", None),
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/audit")
async def get_my_consent_audit(limit: int = 100,
                               subject_id: str = Depends(require_local_staff)):
    return {"events": list_audit(subject_id=subject_id, limit=limit)}
