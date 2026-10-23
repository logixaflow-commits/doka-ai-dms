from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.routes import telegram  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(telegram.router)
    monkeypatch.setenv("TELEGRAM_ACTION_WEBHOOK_SECRET", "test-only-gateway-secret")
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1003992125718")
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", "18")
    monkeypatch.setattr(telegram, "send_telegram_message", AsyncMock(return_value={"ok": True}))
    return TestClient(app)


def test_gateway_action_fails_closed_when_secret_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_ACTION_WEBHOOK_SECRET")
    response = client.post("/api/telegram/action", json={"action": "unknown"})

    assert response.status_code == 503


def test_gateway_action_rejects_missing_or_invalid_secret(client):
    missing = client.post("/api/telegram/action", json={"action": "unknown"})
    invalid = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "wrong"},
        json={"action": "unknown"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_document_mutation_actions_are_not_falsely_reported_as_completed(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "doka_cat_appr:doc_8831", "chat_id": -1003992125718, "topic_id": 18},
    )

    assert response.status_code == 501
    assert "no document was changed" in response.json()["detail"].lower()
    telegram.send_telegram_message.assert_not_awaited()


@pytest.mark.parametrize(
    "action",
    [
        "doka_cat_appr:<script>",
        "doka_quar:doc/../other",
        "doka_dup_archive:",
        "doka_dup_keep:" + ("x" * 129),
    ],
)
def test_document_action_identifier_is_validated_before_processing(client, action):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": action, "chat_id": -1003992125718, "topic_id": 18},
    )

    assert response.status_code == 422
    telegram.send_telegram_message.assert_not_awaited()


def test_unknown_authenticated_action_is_ignored(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "unrecognized", "chat_id": -1003992125718, "topic_id": 18},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    telegram.send_telegram_message.assert_not_awaited()

def test_receipt_fields_are_escaped_before_rendering_telegram_html(client, monkeypatch):
    from app.services.receipt_extractor import ReceiptExtractorService

    malicious = {
        "vendor": "<script>alert(1)</script>",
        "currency": "<b>USD</b>",
        "total_amount": "12.5",
        "category": "<img src=x>",
        "date": None,
        "confidence": 0.9,
    }
    monkeypatch.setattr(
        ReceiptExtractorService,
        "extract_financial_data",
        classmethod(lambda cls, text: malicious),
    )

    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={
            "action": "doka_receipt_scan",
            "raw_message": "receipt text",
            "chat_id": -1003992125718,
            "topic_id": 18,
        },
    )

    assert response.status_code == 200
    sent_message = telegram.send_telegram_message.await_args.args[0]
    assert "<script>" not in sent_message
    assert "<img" not in sent_message
    assert "&lt;script&gt;" in sent_message
    assert "&lt;b&gt;USD&lt;/b&gt;" in sent_message


def test_telegram_webhook_fails_closed_when_secret_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    response = client.post("/api/telegram/webhook", json={"message": {"text": "/help"}})

    assert response.status_code == 503


def test_telegram_webhook_rejects_missing_or_invalid_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-test-secret")
    missing = client.post("/api/telegram/webhook", json={"message": {"text": "/help"}})
    invalid = client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json={"message": {"text": "/help"}},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_telegram_webhook_does_not_claim_document_mutation_succeeded(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-test-secret")
    response = client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-test-secret"},
        json={
            "callback_query": {
                "data": "doka_quar:doc_123",
                "from": {"id": 5},
                "message": {
                    "chat": {"id": -1003992125718},
                    "message_thread_id": 18,
                },
            }
        },
    )

    assert response.status_code == 501
    assert "no document was changed" in response.json()["detail"].lower()
    telegram.send_telegram_message.assert_not_awaited()
