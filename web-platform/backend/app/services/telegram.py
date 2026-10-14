from __future__ import annotations

import logging
from typing import Any
import httpx

from ..core.config import Settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def get_settings():
    return Settings()


async def send_telegram_message(
    text: str,
    *,
    topic_id: int | None = None,
    parse_mode: str = "HTML",
    inline_keyboard: list[list[dict[str, str]]] | None = None,
    disable_web_page_preview: bool = False,
) -> dict[str, Any] | None:
    """Send an asynchronous message to Telegram group/topic for Doka DMS."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    effective_topic = topic_id if topic_id is not None else settings.TELEGRAM_TOPIC_ID

    if not token or not chat_id:
        logger.info("[Telegram:Doka:DryRun] %s", text.replace("\n", " "))
        return None

    if not settings.TELEGRAM_ENABLED:
        logger.debug("[Telegram:Doka:Disabled] %s", text.replace("\n", " "))
        return None

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }

    if effective_topic:
        payload["message_thread_id"] = int(effective_topic)

    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error("Telegram API error (%s): %s", response.status_code, response.text)
                return None
            return response.json()
    except Exception as exc:
        logger.warning("Failed to send Telegram message from Doka: %s", exc)
        return None


async def send_notification(
    title: str,
    details: str,
    *,
    status: str = "INFO",
    topic_id: int | None = None,
    actions: list[tuple[str, str]] | None = None,
) -> dict[str, Any] | None:
    """Send standardized Doka DMS notification."""
    icon_map = {
        "SUCCESS": "✅",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "🚨",
    }
    status_icon = icon_map.get(status.upper(), "📄")

    lines = [
        f"📄 <b>[Doka-DMS]</b> {status_icon} <b>{title}</b>",
        "",
        details,
    ]
    text = "\n".join(lines)

    inline_keyboard = None
    if actions:
        row: list[dict[str, str]] = []
        for label, callback_or_url in actions:
            if callback_or_url.startswith("http://") or callback_or_url.startswith("https://"):
                row.append({"text": label, "url": callback_or_url})
            else:
                row.append({"text": label, "callback_data": callback_or_url})
        inline_keyboard = [row]

    return await send_telegram_message(text, topic_id=topic_id, inline_keyboard=inline_keyboard)


# ==========================================
# Doka Domain Hooks
# ==========================================

async def notify_document_imported(doc_id: str, filename: str, category: str | None = None) -> None:
    """Notify when a document is imported into Workspace."""
    details = f"📁 <b>File:</b> <code>{filename}</code>\n"
    if category:
        details += f"🏷️ <b>Category:</b> {category}\n"
    details += f"🆔 <code>{doc_id}</code>"

    actions = [
        ("✅ Approve Category", f"doka_cat_appr:{doc_id}"),
        ("⚠️ Quarantine", f"doka_quar:{doc_id}"),
    ]
    await send_notification("Document Imported", details, status="INFO", actions=actions)


async def notify_ocr_completed(doc_id: str, filename: str, confidence: float, text_preview: str = "") -> None:
    """Notify when OCR text extraction finishes."""
    conf_pct = round(confidence * 100, 1)
    details = f"📄 <b>File:</b> <code>{filename}</code>\n🎯 <b>OCR Confidence:</b> {conf_pct}%"
    if text_preview:
        short_preview = (text_preview[:120] + "...") if len(text_preview) > 120 else text_preview
        details += f"\n\n💬 <i>\"{short_preview}\"</i>"

    await send_notification("OCR Completed", details, status="SUCCESS")


async def notify_duplicate_detected(original_id: str, duplicate_filename: str) -> None:
    """Notify when duplicate detection finds a redundant file."""
    details = f"⚠️ <b>Duplicate Found:</b> <code>{duplicate_filename}</code>\nMatches original ID: <code>{original_id}</code>"
    actions = [
        ("🗑️ Auto-Move to Archive", f"doka_dup_archive:{original_id}"),
        ("Keep Both", f"doka_dup_keep:{original_id}"),
    ]
    await send_notification("Duplicate Document Detected", details, status="WARNING", actions=actions)


async def notify_backup_status(backup_name: str, success: bool, size_mb: float = 0.0) -> None:
    """Notify when database/file backup finishes."""
    if success:
        details = f"💾 <b>Backup:</b> <code>{backup_name}</code>\n📦 <b>Size:</b> {size_mb:.2f} MB\nStatus: Securely verified."
        await send_notification("Backup Completed", details, status="SUCCESS")
    else:
        details = f"💾 <b>Backup:</b> <code>{backup_name}</code>\n❌ Backup process encountered an error."
        await send_notification("Backup Failed", details, status="ERROR")
