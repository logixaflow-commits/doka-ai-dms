from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
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
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", "8")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "5")
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


def test_document_mutation_actions_reject_legacy_non_numeric_identifiers(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "doka_cat_appr:doc_8831", "chat_id": -1003992125718, "topic_id": 8},
    )

    assert response.status_code == 422
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
        json={"action": action, "chat_id": -1003992125718, "topic_id": 8},
    )

    assert response.status_code == 422
    telegram.send_telegram_message.assert_not_awaited()


def test_unknown_authenticated_action_is_ignored(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "unrecognized", "chat_id": -1003992125718, "topic_id": 8},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    telegram.send_telegram_message.assert_not_awaited()

def test_receipt_scan_fails_closed_without_verified_ocr(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={
            "action": "doka_receipt_scan",
            "raw_message": "receipt text",
            "chat_id": -1003992125718,
            "topic_id": 8,
        },
    )

    assert response.status_code == 501
    assert "verified OCR provider" in response.json()["detail"]
    telegram.send_telegram_message.assert_not_awaited()


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


def test_telegram_webhook_rejects_legacy_non_numeric_document_identifier(client, monkeypatch):
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
                    "message_thread_id": 8,
                },
            }
        },
    )

    assert response.status_code == 422
    telegram.send_telegram_message.assert_not_awaited()


def test_document_mutation_requires_an_allowed_operator(client):
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "doka_cat_appr:123", "user_id": 999, "chat_id": -1003992125718, "topic_id": 8},
    )

    assert response.status_code == 403
    telegram.send_telegram_message.assert_not_awaited()


def test_document_mutation_fails_closed_without_operator_configuration(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS")
    response = client.post(
        "/api/telegram/action",
        headers={"X-Doka-Action-Secret": "test-only-gateway-secret"},
        json={"action": "doka_cat_appr:123", "user_id": 5, "chat_id": -1003992125718, "topic_id": 8},
    )

    assert response.status_code == 503
    telegram.send_telegram_message.assert_not_awaited()


def test_document_mutation_updates_record_and_writes_database_audit(monkeypatch):
    document = SimpleNamespace(id=123, filename="invoice.pdf", status="imported")

    class Query:
        def filter(self, *_args):
            return self

        @staticmethod
        def first():
            return document

    class Session:
        committed = False
        rolled_back = False
        added = []

        @staticmethod
        def query(_model):
            return Query()

        @classmethod
        def add(cls, audit_row):
            cls.added.append(audit_row)

        @classmethod
        def commit(cls):
            cls.committed = True

        @classmethod
        def rollback(cls):
            cls.rolled_back = True

        @staticmethod
        def close():
            return None

    from app.core import database

    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "5")
    monkeypatch.setattr(database, "SessionLocal", Session)
    monkeypatch.setattr(telegram, "log_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(telegram, "send_telegram_message", AsyncMock(return_value={"ok": True}))

    result = asyncio.run(
        telegram._process_action(
            telegram.TelegramActionPayload(
                action="doka_cat_appr:123",
                user_id=5,
                topic_id=8,
            )
        )
    )

    assert result == {
        "status": "success",
        "action": "doka_cat_appr",
        "document_id": 123,
        "new_status": "approved",
    }
    assert document.status == "approved"
    assert Session.committed is True
    assert Session.rolled_back is False
    assert len(Session.added) == 1
    assert Session.added[0].action == "TELEGRAM_DOCUMENT_ACTION"
    assert Session.added[0].document_id == 123


def test_document_mutation_rolls_back_and_hides_internal_error(monkeypatch):
    class Query:
        def filter(self, *_args):
            return self

        @staticmethod
        def first():
            return SimpleNamespace(id=123, filename="invoice.pdf", status="imported")

    class Session:
        rolled_back = False

        @staticmethod
        def query(_model):
            return Query()

        @staticmethod
        def add(_audit_row):
            return None

        @staticmethod
        def commit():
            raise RuntimeError("internal database failure")

        @classmethod
        def rollback(cls):
            cls.rolled_back = True

        @staticmethod
        def close():
            return None

    from app.core import database

    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "5")
    monkeypatch.setattr(database, "SessionLocal", Session)
    monkeypatch.setattr(telegram, "log_audit", lambda *_args, **_kwargs: None)

    with pytest.raises(telegram.HTTPException) as exc_info:
        asyncio.run(
            telegram._process_action(
                telegram.TelegramActionPayload(action="doka_quar:123", user_id=5, topic_id=8)
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Document action could not be completed."
    assert Session.rolled_back is True



def test_telegram_webhook_ignores_messages_outside_the_configured_topic(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-test-secret")
    response = client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-test-secret"},
        json={
            "message": {
                "text": "/help",
                "chat": {"id": -1003992125718},
                "message_thread_id": 19,
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "outside_configured_topic"
    telegram.send_telegram_message.assert_not_awaited()
