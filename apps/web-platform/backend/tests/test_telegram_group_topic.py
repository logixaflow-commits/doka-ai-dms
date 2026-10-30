import asyncio
from types import SimpleNamespace

import pytest

from app.api.routes import telegram
from app.services import telegram as telegram_service


def _configure_target(monkeypatch, *, enabled="true", chat_id="-1003992125718", topic_id="18"):
    monkeypatch.setenv("TELEGRAM_ENABLED", enabled)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", chat_id)
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", topic_id)


def test_telegram_context_accepts_only_configured_group_topic(monkeypatch):
    _configure_target(monkeypatch)

    assert telegram._telegram_context_allowed(-1003992125718, 18)
    assert telegram._telegram_context_allowed("-1003992125718", 18)
    assert not telegram._telegram_context_allowed(-1003992125719, 18)
    assert not telegram._telegram_context_allowed(-1003992125718, 19)
    assert not telegram._telegram_context_allowed(-1003992125718, None)


@pytest.mark.parametrize(
    ("enabled", "chat_id", "topic_id"),
    [
        ("false", "-1003992125718", "18"),
        ("true", "", "18"),
        ("true", "-1003992125718", ""),
        ("true", "-1003992125718", "general"),
    ],
)
def test_telegram_context_fails_closed_when_target_is_not_configured(
    monkeypatch, enabled, chat_id, topic_id
):
    _configure_target(
        monkeypatch,
        enabled=enabled,
        chat_id=chat_id,
        topic_id=topic_id,
    )

    assert not telegram._telegram_context_allowed(-1003992125718, 18)


def test_outbound_messages_are_pinned_to_configured_topic(monkeypatch):
    calls = []
    monkeypatch.setattr(
        telegram_service,
        "get_settings",
        lambda: SimpleNamespace(
            TELEGRAM_BOT_TOKEN="test-token",
            TELEGRAM_CHAT_ID="-1003992125718",
            TELEGRAM_TOPIC_ID=18,
            TELEGRAM_ENABLED=True,
        ),
    )

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"ok": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, *, json):
            calls.append({"url": url, "payload": json})
            return FakeResponse()

    monkeypatch.setattr(telegram_service.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = asyncio.run(telegram_service.send_telegram_message("test", topic_id=99))

    assert result == {"ok": True}
    assert calls[0]["payload"]["chat_id"] == "-1003992125718"
    assert calls[0]["payload"]["message_thread_id"] == 18


def test_telegram_receipt_scan_fails_closed_without_verified_ocr(monkeypatch):
    sent_messages = []
    monkeypatch.setattr(
        telegram,
        "send_telegram_message",
        lambda *args, **kwargs: sent_messages.append((args, kwargs)),
    )
    payload = telegram.TelegramActionPayload(
        action="doka_receipt_scan",
        chat_id="-1003992125718",
        topic_id=18,
        raw_message="ACME STORE\\nTOTAL 12500 MMK",
    )

    with pytest.raises(telegram.HTTPException) as exc_info:
        asyncio.run(telegram._process_action(payload))

    assert exc_info.value.status_code == 501
    assert sent_messages == []

