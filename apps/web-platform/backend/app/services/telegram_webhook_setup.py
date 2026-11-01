from __future__ import annotations

import logging
import os

import httpx

from ..core.config import Settings

logger = logging.getLogger(__name__)


def get_settings():
    return Settings()


async def configure_telegram_webhook() -> None:
    """Register the Telegram webhook URL and secret with the Bot API."""
    settings = get_settings()

    if not settings.TELEGRAM_ENABLED:
        logger.info("Telegram webhook setup skipped: Telegram integration is disabled")
        return

    token = settings.TELEGRAM_BOT_TOKEN
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    base_url = os.getenv("TELEGRAM_WEBHOOK_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")

    if not token:
        logger.warning("Telegram webhook setup skipped: bot token is not configured")
        return
    if not base_url:
        logger.warning("Telegram webhook setup skipped: TELEGRAM_WEBHOOK_URL and RENDER_EXTERNAL_URL are empty")
        return
    if len(secret) < 32:
        logger.warning("Telegram webhook setup skipped: TELEGRAM_WEBHOOK_SECRET must be at least 32 characters")
        return

    webhook_url = base_url if base_url.endswith("/api/telegram/webhook") else base_url.rstrip("/") + "/api/telegram/webhook"
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {
        "url": webhook_url,
        "secret_token": secret,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("ok") is True:
                logger.info("Telegram webhook configured successfully for Doka AI DMS")
            else:
                logger.error("Telegram webhook setup failed: Telegram API returned ok=false")
                return

            # Register bot commands for the group
            try:
                chat_id = settings.TELEGRAM_CHAT_ID
                command_payload = {
                    "commands": [
                        {"command": "start", "description": "Connect to Doka DMS topic"},
                        {"command": "help", "description": "Show available commands"},
                        {"command": "status", "description": "Check Doka DMS service status"},
                    ],
                }
                if chat_id:
                    command_payload["scope"] = {"type": "chat", "chat_id": int(chat_id)}

                cmd_response = await client.post(
                    f"https://api.telegram.org/bot{token}/setMyCommands",
                    json=command_payload,
                )
                cmd_response.raise_for_status()
                cmd_result = cmd_response.json()
                if cmd_result.get("ok") is True:
                    logger.info("Telegram command menu configured for Doka AI DMS group")
                else:
                    logger.warning("Telegram command menu setup failed: API returned ok=false")
            except Exception as exc:
                logger.warning("Telegram command menu setup failed (%s)", type(exc).__name__)

    except Exception as exc:
        logger.error("Telegram webhook setup failed (%s)", type(exc).__name__)
