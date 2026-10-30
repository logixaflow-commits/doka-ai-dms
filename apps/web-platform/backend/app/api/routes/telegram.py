from __future__ import annotations

import hmac
import logging
import os
import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...services.telegram import send_telegram_message

logger = logging.getLogger("doka.telegram.action")
router = APIRouter(prefix="/api/telegram", tags=["Telegram"])
FRONTEND_URL = os.getenv("FRONTEND_BASE_URL", "https://doka-ai-dms-frontend.onrender.com")
_DOCUMENT_ACTIONS = {"doka_cat_appr", "doka_quar", "doka_dup_archive", "doka_dup_keep"}
_DOCUMENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class TelegramActionPayload(BaseModel):
    action: str = Field(min_length=1, max_length=256)
    chat_id: int | str | None = None
    topic_id: int | None = None
    user_id: int | None = None
    username: str | None = Field(default=None, max_length=128)
    raw_message: str | None = Field(default=None, max_length=4000)


def _authorize_secret(secret_header: str | None, env_name: str, service_name: str) -> None:
    """Fail closed unless a dedicated shared secret is configured and presented."""
    configured = os.getenv(env_name, "").strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_name} is not configured.",
        )
    if not secret_header or not hmac.compare_digest(secret_header, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid gateway authentication.",
        )


def _authorize_gateway(secret_header: str | None) -> None:
    _authorize_secret(secret_header, "TELEGRAM_ACTION_WEBHOOK_SECRET", "Telegram action gateway")


def _authorize_telegram_webhook(secret_header: str | None) -> None:
    _authorize_secret(secret_header, "TELEGRAM_WEBHOOK_SECRET", "Telegram webhook")


def _telegram_context_allowed(chat_id: int | str | None, topic_id: int | None) -> bool:
    """Fail closed unless an update comes from the one configured group topic."""
    if os.getenv("TELEGRAM_ENABLED", "false").strip().lower() != "true":
        return False

    expected_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    configured_topic = os.getenv("TELEGRAM_TOPIC_ID", "").strip()
    if not expected_chat_id or not configured_topic.isdigit() or topic_id is None:
        return False

    try:
        return str(chat_id) == expected_chat_id and int(topic_id) == int(configured_topic)
    except (TypeError, ValueError):
        return False


def _format_live_status(
    database_status: dict[str, Any],
    ocr_counts: dict[str, int] | None,
) -> tuple[str, dict[str, Any]]:
    database_label = "healthy" if database_status.get("status") == "connected" else "unavailable"
    if ocr_counts is None:
        ocr_label = "unavailable"
        normalized_counts = None
    else:
        normalized_counts = {
            name: max(0, int(ocr_counts.get(name, 0)))
            for name in ("queued", "processing", "completed", "failed")
        }
        ocr_label = (
            f"{normalized_counts['processing']} processing, "
            f"{normalized_counts['queued']} queued; "
            f"{normalized_counts['completed']} completed, "
            f"{normalized_counts['failed']} failed"
        )
    message = (
        "ℹ️ <b>Doka-DMS live status</b>\n"
        f"• Database: {database_label}\n"
        f"• OCR queue: {ocr_label}\n"
        "• Storage: not checked by this command"
    )
    return message, {"database": database_label, "ocr_queue": normalized_counts}


def _get_ocr_queue_counts() -> dict[str, int] | None:
    """Read aggregate OCR status only; never expose database errors to Telegram."""
    from sqlalchemy import text

    from ...core.database import SessionLocal

    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT status, COUNT(*) FROM ocr_batch_jobs GROUP BY status")
        )
        return {str(row[0]): int(row[1]) for row in rows}
    except Exception:  # noqa: BLE001 - schema may be absent until the migration is deployed
        logger.warning("OCR queue status unavailable; database migration may be pending.")
        return None
    finally:
        db.close()


async def _process_action(payload: TelegramActionPayload) -> dict[str, Any]:
    """Process only actions supported by this runtime; never fake a document mutation."""
    action_type, separator, action_value = payload.action.partition(":")
    logger.info("Doka received Telegram action type: %s", action_type)

    if action_type in _DOCUMENT_ACTIONS:
        if not separator or not _DOCUMENT_ID.fullmatch(action_value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid document action identifier.",
            )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Document actions are not enabled in this runtime; no document was changed.",
        )

    if action_type == "doka_receipt_scan":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Receipt OCR is not connected to a verified OCR provider; no receipt data was extracted or saved.",
        )

    return {"status": "ignored", "action": action_type}


@router.post("/action")
async def handle_telegram_action(
    payload: TelegramActionPayload,
    x_doka_action_secret: str | None = Header(default=None, alias="X-Doka-Action-Secret"),
) -> dict[str, Any]:
    """Authenticated internal gateway endpoint, not a public Telegram webhook."""
    _authorize_gateway(x_doka_action_secret)
    if not _telegram_context_allowed(payload.chat_id, payload.topic_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram actions are restricted to the configured group topic.",
        )
    return await _process_action(payload)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
) -> dict[str, Any]:
    """Receive Telegram updates only when Telegram's configured webhook token is valid."""
    _authorize_telegram_webhook(x_telegram_bot_api_secret_token)
    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid Telegram update.")

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        topic_id = message.get("message_thread_id")
        if not _telegram_context_allowed(chat.get("id"), topic_id):
            return {"ok": True, "status": "ignored", "reason": "outside_configured_topic"}
        sender = callback.get("from") or {}
        payload = TelegramActionPayload(
            action=str(callback.get("data") or "invalid"),
            chat_id=chat.get("id"),
            topic_id=topic_id,
            user_id=sender.get("id"),
            username=sender.get("username"),
        )
        return await _process_action(payload)

    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True, "status": "ignored"}
    chat = message.get("chat") or {}
    topic_id = message.get("message_thread_id")
    if not _telegram_context_allowed(chat.get("id"), topic_id):
        return {"ok": True, "status": "ignored", "reason": "outside_configured_topic"}
    text = message.get("text")
    if not isinstance(text, str):
        return {"ok": True, "status": "ignored"}
    text = text.strip()

    if text.startswith(("/start", "/help")):
        help_text = (
            "📄 <b>Doka-AI-DMS Document Commands:</b>\n\n"
            "• <code>/status</code> — Check service status\n"
            "• <code>/morning_brief</code> — Today's intake briefing\n"
            "• <code>/ask [query]</code> — Ask about document search availability\n\n"
            "👇 Open the Document Vault from the configured Mini App."
        )
        buttons = [[{"text": "📄 Open Document Vault", "web_app": {"url": FRONTEND_URL}}]]
        await send_telegram_message(help_text, topic_id=topic_id, inline_keyboard=buttons)
        return {"ok": True, "command": "help"}

    if text.startswith("/status"):
        from ...core.database import get_db_status

        database_status = get_db_status()
        ocr_counts = _get_ocr_queue_counts() if database_status.get("status") == "connected" else None
        reply, snapshot = _format_live_status(database_status, ocr_counts)
        await send_telegram_message(reply, topic_id=topic_id)
        return {"ok": True, "command": "status", **snapshot}

    if text.startswith(("/morning_brief", "/digest")):
        await send_telegram_message(
            "ℹ️ The automated morning briefing is not connected to a verified live document query yet.",
            topic_id=topic_id,
        )
        return {"ok": True, "command": "morning_brief", "status": "not_configured"}

    if text.startswith("/ask"):
        await send_telegram_message(
            "ℹ️ Document search is not connected to this Telegram command yet.",
            topic_id=topic_id,
        )
        return {"ok": True, "command": "ask", "status": "not_configured"}

    return {"ok": True, "status": "ignored"}
