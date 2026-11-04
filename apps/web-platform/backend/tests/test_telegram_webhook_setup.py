from __future__ import annotations

import asyncio

from app.services import telegram_webhook_setup


def test_webhook_auto_registration_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_AUTOREGISTER", raising=False)

    def unexpected_settings():
        raise AssertionError("Settings must not be loaded when this runtime does not own the webhook")

    monkeypatch.setattr(telegram_webhook_setup, "get_settings", unexpected_settings)

    asyncio.run(telegram_webhook_setup.configure_telegram_webhook())


def test_webhook_auto_registration_requires_explicit_true(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_AUTOREGISTER", "false")

    def unexpected_settings():
        raise AssertionError("Settings must not be loaded when auto-registration is disabled")

    monkeypatch.setattr(telegram_webhook_setup, "get_settings", unexpected_settings)

    asyncio.run(telegram_webhook_setup.configure_telegram_webhook())
