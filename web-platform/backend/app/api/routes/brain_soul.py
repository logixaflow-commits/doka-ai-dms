"""Brain Soul Layer — REST endpoints for DOKA AI DMS.

Soul File: personal context key-value store that makes every AI interaction
in DOKA aware of who you are, what you care about, and how you work.

Endpoints:
  GET    /api/brain/soul/context           — list Soul File entries
  POST   /api/brain/soul/context           — upsert entry
  DELETE /api/brain/soul/context/{key}     — remove entry
  GET    /api/brain/soul/context/prefix    — preview LLM system-prompt prefix
  GET    /api/brain/soul/syntheses         — list weekly document synthesis snapshots
  POST   /api/brain/soul/synthesize        — manually trigger synthesis
  GET    /api/brain/soul/status            — health overview
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.local_security import require_local_staff
from app.models.brain_soul import Base, BrainSoulContext, BrainSoulSynthesis

logger = logging.getLogger("doka.brain_soul")

router = APIRouter(
    prefix="/api/brain/soul",
    tags=["Brain Soul"],
    dependencies=[Depends(require_local_staff)],
)

# ── ensure tables exist at import time (safe no-op if already present) ────────
try:
    from app.core.database import engine
    Base.metadata.create_all(bind=engine)
except Exception as _boot_exc:
    logger.warning("brain_soul: could not auto-create tables at startup — %s", _boot_exc)


# ── default Soul File entries (seeded once on first use) ─────────────────────
_SOUL_DEFAULTS = [
    ("operator_name",    "Doka User",                   "Who is using this DOKA instance"),
    ("document_domains", "work documents, PDFs, invoices", "Main types of documents managed"),
    ("search_language",  "English / Myanmar",            "Preferred language for AI summaries"),
    ("ai_tone",          "concise and factual",          "Preferred tone for AI-generated content"),
    ("brain_purpose",    "Personal document management AI — search, summarise, temporal recall", "What this DOKA brain is for"),
]


def _seed_defaults(db: Session) -> None:
    """Insert default Soul File entries on first use — never overwrites."""
    for key, value, description in _SOUL_DEFAULTS:
        existing = db.query(BrainSoulContext).filter_by(context_key=key).first()
        if existing is None:
            db.add(BrainSoulContext(
                context_key=key,
                context_value=value,
                description=description,
                updated_by="system",
            ))
    db.commit()


# ── request/response models ───────────────────────────────────────────────────

class ContextUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=4000)
    description: str = Field(default="", max_length=500)


class SynthesizeRequest(BaseModel):
    topic: str = Field(default="documents", min_length=1, max_length=80)
    force: bool = False


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_system_prefix(db: Session) -> str:
    """Build LLM system-prompt prefix from active Soul File entries."""
    try:
        rows = db.query(BrainSoulContext).filter_by(is_active=True).order_by(BrainSoulContext.context_key).all()
        if not rows:
            return ""
        lines = ["[Personal Brain Context]"]
        for r in rows:
            desc = f" ({r.description})" if r.description else ""
            lines.append(f"• {r.context_key}{desc}: {r.context_value}")
        lines.append("")
        return "\n".join(lines)
    except Exception:
        return ""


# ── context endpoints ─────────────────────────────────────────────────────────

@router.get("/context")
def list_context(db: Session = Depends(get_db)) -> dict:
    """Return all Soul File entries."""
    _seed_defaults(db)
    rows = db.query(BrainSoulContext).order_by(BrainSoulContext.context_key).all()
    return {"entries": [r.to_dict() for r in rows], "total": len(rows)}


@router.post("/context", status_code=201)
def upsert_context(payload: ContextUpsert, db: Session = Depends(get_db)) -> dict:
    """Insert or update a Soul File entry."""
    existing = db.query(BrainSoulContext).filter_by(context_key=payload.key).first()
    if existing:
        existing.context_value = payload.value
        existing.description = payload.description
        existing.updated_by = "user"
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return {"entry": existing.to_dict()}
    entry = BrainSoulContext(
        context_key=payload.key,
        context_value=payload.value,
        description=payload.description,
        updated_by="user",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"entry": entry.to_dict()}


@router.delete("/context/{key}")
def delete_context(key: str, db: Session = Depends(get_db)) -> dict:
    """Delete a Soul File entry by key."""
    entry = db.query(BrainSoulContext).filter_by(context_key=key).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"No soul context entry with key '{key}'")
    db.delete(entry)
    db.commit()
    return {"deleted": True, "key": key}


@router.get("/context/prefix")
def preview_prefix(db: Session = Depends(get_db)) -> dict:
    """Preview the LLM system-prompt prefix Brain Soul would inject."""
    prefix = _build_system_prefix(db)
    return {"prefix": prefix, "empty": not bool(prefix.strip())}


# ── synthesis endpoints ───────────────────────────────────────────────────────

@router.get("/syntheses")
def list_syntheses(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    """Return recent weekly synthesis snapshots, newest first."""
    rows = (
        db.query(BrainSoulSynthesis)
        .order_by(BrainSoulSynthesis.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"syntheses": [r.to_dict() for r in rows], "total": len(rows)}


@router.post("/synthesize", status_code=202)
async def trigger_synthesis(
    payload: SynthesizeRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Manually trigger a weekly synthesis of recent documents.

    Gathers documents processed in the past 7 days, summarises them with the
    configured AI provider, then saves a BrainSoulSynthesis snapshot.
    """
    now = datetime.now(timezone.utc)
    period_label = now.strftime("%Y-W%W")
    week_ago = now - timedelta(days=7)
    topic = payload.topic.strip() or "documents"

    # Check for existing synthesis (skip unless force=True)
    if not payload.force:
        existing = (
            db.query(BrainSoulSynthesis)
            .filter_by(period_label=period_label, topic=topic)
            .first()
        )
        if existing:
            return {
                "status": "skipped",
                "reason": "Synthesis already exists for this period. Use force=true to regenerate.",
                "synthesis": existing.to_dict(),
            }

    # ── gather recent document data ────────────────────────────────────────
    items: list[str] = []
    item_ids: list = []
    try:
        # Try to query documents table (may not exist in all editions)
        result = db.execute(
            text(
                "SELECT id, original_filename, category, ocr_text "
                "FROM documents "
                "WHERE created_at >= :since "
                "ORDER BY created_at DESC "
                "LIMIT 30"
            ),
            {"since": week_ago},
        )
        for row in result.mappings():
            snippet = ((row.get("ocr_text") or "") + " " + (row.get("category") or ""))[:250].strip().replace("\n", " ")
            items.append(f"[{row.get('category', 'doc')}] {row.get('original_filename', 'unknown')}: {snippet}")
            item_ids.append(f"doc:{row['id']}")
    except Exception:
        pass  # Documents table may not be in this edition

    # Also pull any workspace import sessions as context
    try:
        result = db.execute(
            text(
                "SELECT id, status FROM workspace_import_sessions "
                "WHERE created_at >= :since ORDER BY created_at DESC LIMIT 10"
            ),
            {"since": week_ago},
        )
        for row in result.mappings():
            items.append(f"[workspace] import session {row['id']}: status={row['status']}")
            item_ids.append(f"session:{row['id']}")
    except Exception:
        pass

    if len(items) < 2:
        return {
            "status": "skipped",
            "reason": f"Only {len(items)} document(s) found in the past 7 days (need ≥ 2 for meaningful synthesis)",
            "period_label": period_label,
            "topic": topic,
        }

    # Build prompt
    combined = "\n".join(items)
    system_prompt = (
        "You are a personal document intelligence assistant. "
        "Based on the documents processed this week, write a concise synthesis "
        "(200–350 words) that covers:\n"
        "1. What types of documents were processed\n"
        "2. Key themes, categories, or patterns you noticed\n"
        "3. Any follow-up actions the user might want to take\n\n"
        "Write in clear, practical prose. Be direct and useful, not verbose."
    )
    user_prompt = (
        f"Topic: {topic}\n"
        f"Period: {period_label} (past 7 days)\n"
        f"Documents: {len(items)} items\n\n"
        f"{combined}\n\nWrite the weekly synthesis now."
    )

    # ── call LLM ─────────────────────────────────────────────────────────────
    synthesis_text: str
    provider: str | None = None
    try:
        from app.services.unified_ai_service import UnifiedAIService
        ai = UnifiedAIService()
        synthesis_text = await ai.complete(
            system_prompt=system_prompt,
            user_message=user_prompt,
        )
        provider = ai._last_provider if hasattr(ai, "_last_provider") else "unified_ai"
    except Exception as llm_exc:
        logger.warning("synthesize: LLM failed — %s; using extractive fallback", llm_exc)
        synthesis_text = "\n\n".join(f"• {item}" for item in items[:10])
        provider = "extractive_fallback"

    if not synthesis_text.strip():
        raise HTTPException(status_code=500, detail="AI returned empty synthesis text")

    # ── persist ───────────────────────────────────────────────────────────────
    if payload.force:
        db.query(BrainSoulSynthesis).filter_by(
            period_label=period_label, topic=topic
        ).delete()
        db.commit()

    snapshot = BrainSoulSynthesis(
        period_label=period_label,
        period_start=week_ago,
        period_end=now,
        topic=topic,
        synthesis_text=synthesis_text.strip(),
        source_item_ids=json.dumps(item_ids),
        item_count=len(item_ids),
        provider=provider,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "status": "created",
        "synthesis": snapshot.to_dict(),
        "item_count": len(items),
        "provider": provider,
    }


# ── status endpoint ───────────────────────────────────────────────────────────

@router.get("/status")
def soul_status(db: Session = Depends(get_db)) -> dict:
    """Health overview for the Brain Soul layer."""
    context_count = 0
    synthesis_count = 0
    latest_at: str | None = None
    tables_ready = False

    try:
        context_count = db.query(BrainSoulContext).filter_by(is_active=True).count()
        synthesis_count = db.query(BrainSoulSynthesis).count()
        latest = db.query(BrainSoulSynthesis).order_by(BrainSoulSynthesis.created_at.desc()).first()
        if latest:
            latest_at = latest.created_at.isoformat() if latest.created_at else None
        tables_ready = True
    except Exception:
        pass

    return {
        "tables_ready": tables_ready,
        "active_context_entries": context_count,
        "total_syntheses": synthesis_count,
        "latest_synthesis_at": latest_at,
    }
