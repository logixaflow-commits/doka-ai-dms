from __future__ import annotations

import html
import hmac
import logging
import os
import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from ...services.telegram import send_telegram_message

logger = logging.getLogger("doka.telegram.action")

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])
_DOCUMENT_ACTIONS = {
    "doka_cat_appr",
    "doka_quar",
    "doka_dup_archive",
    "doka_dup_keep",
}
_DOCUMENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class TelegramActionPayload(BaseModel):
    action: str = Field(min_length=1, max_length=256)
    chat_id: int | str | None = None
    topic_id: int | None = None
    user_id: int | None = None
    username: str | None = Field(default=None, max_length=128)
    raw_message: str | None = Field(default=None, max_length=4000)


def _authorize_gateway(secret_header: str | None) -> None:
    """Fail closed unless the gateway is configured with a dedicated shared secret."""
    configured = os.getenv("TELEGRAM_ACTION_WEBHOOK_SECRET", "").strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram action gateway is not configured.",
        )
    if not secret_header or not hmac.compare_digest(secret_header, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid gateway authentication.",
        )


@router.post("/action")
async def handle_telegram_action(
    payload: TelegramActionPayload,
    x_doka_action_secret: str | None = Header(default=None, alias="X-Doka-Action-Secret"),
) -> dict[str, Any]:
    """Accept authenticated gateway actions without claiming unsupported mutations."""
    _authorize_gateway(x_doka_action_secret)

    action_type, separator, action_value = payload.action.partition(":")
    logger.info("Doka received Telegram gateway action type: %s", action_type)

    # These actions are shown in Telegram, but no safe document-mutation service is
    # wired into the active Personal Local runtime yet. Do not pretend a mutation ran.
    if action_type in _DOCUMENT_ACTIONS:
        if not separator or not _DOCUMENT_ID.fullmatch(action_value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid document action identifier.",
            )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Document actions are not enabled in this runtime; no document was changed.",
        )

    if payload.action == "doka_receipt_scan" and payload.raw_message:
        from ...services.receipt_extractor import ReceiptExtractorService

        extracted = ReceiptExtractorService.extract_financial_data(payload.raw_message)
        vendor = html.escape(str(extracted.get("vendor", "")))
        currency = html.escape(str(extracted.get("currency", "")))
        category = html.escape(str(extracted.get("category", "")))
        date_value = html.escape(str(extracted.get("date") or "N/A"))
        try:
            total = float(extracted.get("total_amount", 0))
        except (TypeError, ValueError):
            total = 0.0
        try:
            confidence = int(float(extracted.get("confidence", 0)) * 100)
        except (TypeError, ValueError):
            confidence = 0
        reply = (
            "🧾 <b>Instant Receipt Extracted:</b>\n"
            f"🏪 <b>Vendor:</b> {vendor}\n"
            f"💰 <b>Total:</b> {currency} {total:,.2f}\n"
            f"🏷️ <b>Category:</b> {category}\n"
            f"📅 <b>Date:</b> {date_value}\n"
            f"🎯 <b>Confidence:</b> {confidence}%"
        )
        await send_telegram_message(reply, topic_id=payload.topic_id)
        return {"status": "ok", "action": "receipt_scanned", "data": extracted}

    return {"status": "ignored", "action": action_type}
