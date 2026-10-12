"""End-to-end tests for authenticated, exact-scope AI consent endpoints."""
from __future__ import annotations

import pytest\n\nfrom fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app
from app.services.consent_store import get_consent_grant


def _client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "consent-test-admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "synthetic-consent-password")
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(settings, "WORKING_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    return TestClient(create_app())


def _token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "username": "consent-test-admin",
            "password": "synthetic-consent-password",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_consent_routes_require_authenticated_local_subject(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    assert client.get("/api/ai/consent").status_code == 401
    assert client.put(
        "/api/ai/consent",
        json={"purpose": "document_analysis", "scope": "document:42", "granted": True},
    ).status_code == 401

    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put(
        "/api/ai/consent?subject_id=attacker",
        headers=headers,
        json={"purpose": "document_analysis", "scope": "document:42", "granted": True},
    )
    assert response.status_code == 200
    assert response.json()["subject_id"] == "consent-test-admin"
    assert get_consent_grant(
        subject_id="consent-test-admin", purpose="document_analysis", scope="document:42"
    ) is not None
    assert get_consent_grant(
        subject_id="attacker", purpose="document_analysis", scope="document:42"
    ) is None


def test_consent_revocation_and_audit_are_visible_only_in_authenticated_scope(
    monkeypatch, tmp_path
):
    client = _client(monkeypatch, tmp_path)
    headers = {"Authorization": f"Bearer {_token(client)}"}
    scope = "document:private-42"

    granted = client.put(
        "/api/ai/consent",
        headers=headers,
        json={"purpose": "embedding", "scope": scope, "granted": True},
    )
    assert granted.status_code == 200
    assert get_consent_grant(
        subject_id="consent-test-admin", purpose="embedding", scope=scope
    ) is not None

    revoked = client.put(
        "/api/ai/consent",
        headers=headers,
        json={"purpose": "embedding", "scope": scope, "granted": False},
    )
    assert revoked.status_code == 200
    assert get_consent_grant(
        subject_id="consent-test-admin", purpose="embedding", scope=scope
    ) is None

    listed = client.get("/api/ai/consent", headers=headers)
    assert listed.status_code == 200
    entry = next(row for row in listed.json()["consents"] if row["scope"] == scope)
    assert entry["granted"] is False

    audit = client.get("/api/ai/consent/audit", headers=headers)
    assert audit.status_code == 200
    assert [row["action"] for row in reversed(audit.json()["events"])] == [
        "granted", "revoked"
    ]


def test_consent_route_rejects_unsupported_purpose(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.put(
        "/api/ai/consent",
        headers={"Authorization": f"Bearer {_token(client)}"},
        json={"purpose": "anything", "scope": "document:42", "granted": True},
    )
    assert response.status_code == 422


def test_consent_revision_and_audit_are_durable_and_append_only(monkeypatch, tmp_path):
    import sqlite3

    client = _client(monkeypatch, tmp_path)
    headers = {"Authorization": f"Bearer {_token(client)}"}
    payload = {"purpose": "document_analysis", "scope": "document:revision-9", "granted": True}

    first = client.put("/api/ai/consent", headers=headers, json=payload)
    repeated = client.put("/api/ai/consent", headers=headers, json=payload)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["revision"] == repeated.json()["revision"] == 1

    revoked = client.put(
        "/api/ai/consent",
        headers=headers,
        json={**payload, "granted": False},
    )
    regranted = client.put("/api/ai/consent", headers=headers, json=payload)
    assert revoked.status_code == regranted.status_code == 200
    assert revoked.json()["revision"] == 2
    assert regranted.json()["revision"] == 3

    audit = client.get("/api/ai/consent/audit?limit=2", headers=headers)
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()["events"]] == ["granted", "revoked"]

    db_path = tmp_path / "auth.sqlite3"
    with sqlite3.connect(db_path) as db:
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            db.execute("UPDATE ai_consent_audit SET action='denied' WHERE id=1")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            db.execute("DELETE FROM ai_consent_audit WHERE id=1")
