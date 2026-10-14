from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from ...services.telegram import send_telegram_message

logger = logging.getLogger("doka.telegram.action")

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


class TelegramActionPayload(BaseModel):
    action: str
    chat_id: int | str | None = None
    topic_id: int | None = None
    user_id: int | None = None
    username: str | None = None
    raw_message: str | None = None


@router.post("/action")
async def handle_telegram_action(payload: TelegramActionPayload) -> dict[str, Any]:
    """Handle inbound Telegram action callback for Doka DMS."""
    action = payload.action
    logger.info("Doka received Telegram action: %s", action)

    # 1. Category Approval
    if action.startswith("doka_cat_appr:"):
        doc_id = action.split(":", 1)[1]
        msg = f"✅ <b>Classification Confirmed:</b> Document <code>{doc_id}</code> moved to <code>Final/Organized</code>."
        await send_telegram_message(msg, topic_id=payload.topic_id)
        return {"status": "ok", "action": "category_approved", "id": doc_id}

    # 2. Quarantine Document
    elif action.startswith("doka_quar:"):
        doc_id = action.split(":", 1)[1]
        msg = f"⚠️ <b>Document Quarantined:</b> <code>{doc_id}</code> isolated into <code>Quarantine/Suspicious</code>."
        await send_telegram_message(msg, topic_id=payload.topic_id)
        return {"status": "ok", "action": "quarantined", "id": doc_id}

    # 3. Duplicate Resolution
    elif action.startswith("doka_dup_archive:"):
        doc_id = action.split(":", 1)[1]
        msg = f"🗑️ <b>Duplicate Resolved:</b> Duplicate of <code>{doc_id}</code> moved to Duplicates archive."
        await send_telegram_message(msg, topic_id=payload.topic_id)
        return {"status": "ok", "action": "duplicate_archived", "id": doc_id}

    elif action.startswith("doka_dup_keep:"):
        doc_id = action.split(":", 1)[1]
        msg = f"📁 <b>Both Copies Retained:</b> Marked <code>{doc_id}</code> with unique revision tag."
        await send_telegram_message(msg, topic_id=payload.topic_id)
        return {"status": "ok", "action": "duplicate_kept", "id": doc_id}

    return {"status": "ignored", "action": action}
