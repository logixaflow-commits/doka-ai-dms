"""End-to-end tests for authenticated, exact-scope AI consent endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

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
