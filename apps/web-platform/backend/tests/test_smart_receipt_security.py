"""Security regression tests for the receipt upload endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


def _client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "receipt-test-admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "synthetic-receipt-password")
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(settings, "WORKING_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    return TestClient(create_app())


def _token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "receipt-test-admin", "password": "synthetic-receipt-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_receipt_endpoint_requires_authentication(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/api/documents/receipt/scan-vision",
        files={"file": ("receipt.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 401


def test_receipt_endpoint_does_not_return_synthetic_financial_data(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/api/documents/receipt/scan-vision",
        headers={"Authorization": f"Bearer {_token(client)}"},
        files={"file": ("receipt.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 501
    assert response.json()["detail"] == (
        "Receipt extraction is not configured. No receipt data was processed or verified."
    )
    assert "total_amount" not in response.json()


def test_receipt_endpoint_rejects_unsupported_mime(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/api/documents/receipt/scan-vision",
        headers={"Authorization": f"Bearer {_token(client)}"},
        files={"file": ("receipt.txt", b"not a receipt image", "text/plain")},
    )
    assert response.status_code == 415


def test_receipt_endpoint_enforces_actual_upload_size(monkeypatch, tmp_path):
    from app.api.routes import smart_receipt

    monkeypatch.setattr(smart_receipt, "MAX_RECEIPT_UPLOAD_BYTES", 4)
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/api/documents/receipt/scan-vision",
        headers={"Authorization": f"Bearer {_token(client)}"},
        files={"file": ("receipt.pdf", b"12345", "application/pdf")},
    )
    assert response.status_code == 413
