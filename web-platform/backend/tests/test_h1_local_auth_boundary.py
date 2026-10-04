import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.core.auth_boundary import database_user_id_from_payload
from app.core.config import settings
from app.core.local_security import (
    create_local_access_token,
    decode_local_token,
    is_local_auth_payload,
    require_local_staff,
)
from app.core.supabase_auth import require_authenticated_user
from app.main import create_app


def _signed_non_object_payload(key: str) -> str:
    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    signing_input = ".".join(
        (
            encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8")),
            encode(json.dumps(["not", "claims"]).encode("utf-8")),
        )
    )
    signature = hmac.new(
        key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{encode(signature)}"


def test_local_login_and_protected_workspace_require_valid_local_session(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "batch0-local-admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "synthetic-local-password")
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")
    monkeypatch.setattr(
        "app.core.supabase_auth.httpx.AsyncClient",
        lambda **_kwargs: pytest.fail("Personal Local attempted Supabase authentication."),
    )
    client = TestClient(create_app())

    assert client.get("/api/workspace/imports").status_code == 401

    wrong_password = client.post(
        "/api/auth/login",
        json={"username": "batch0-local-admin", "password": "synthetic-wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert "synthetic-wrong-password" not in wrong_password.text

    login = client.post(
        "/api/auth/login",
        json={"username": "batch0-local-admin", "password": "synthetic-local-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get(
        "/api/workspace/imports",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["username"] == "batch0-local-admin"

    malformed_token = "malformed"
    expired_token = jwt.encode(
        {
            "sub": "batch0-local-admin",
            "role": "admin",
            "type": "access",
            "auth_provider": "personal-local",
            "jti": "expired-test-token",
            "sid": "expired-test-session",
            "sid_exp": 1,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    cloud_token = jwt.encode(
        {
            "sub": "27",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    non_object_payload_token = _signed_non_object_payload(settings.SECRET_KEY)
    for bad_token in (
        malformed_token,
        expired_token,
        cloud_token,
        non_object_payload_token,
    ):
        rejected = client.get(
            "/api/workspace/imports",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert rejected.status_code == 401
        assert bad_token not in rejected.text


def test_cloud_and_personal_local_apps_mount_separate_auth_routes(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    local_paths = {route.path for route in create_app().routes}

    from app.cloud_main import create_app as create_cloud_app

    cloud_paths = {route.path for route in create_cloud_app().routes}

    assert "/api/auth/login" in local_paths
    assert "/api/workspace/imports" in local_paths
    assert "/api/documents" not in local_paths
    assert "/api/storage/objects" not in local_paths
    assert "/api/auth/login" not in cloud_paths
    assert "/api/workspace/imports" not in cloud_paths
    assert "/api/documents" in cloud_paths
    assert "/api/storage/objects" in cloud_paths


def test_local_tokens_are_distinguishable_from_legacy_database_tokens(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    local_token = create_local_access_token("27")
    local_payload = jwt.decode(
        local_token, settings.SECRET_KEY, algorithms=["HS256"]
    )
    assert is_local_auth_payload(local_payload)
    assert database_user_id_from_payload(local_payload) is None
    assert decode_local_token(local_token)["sub"] == "27"

    legacy_local_payload = {
        "sub": "27",
        "role": "admin",
        "type": "access",
        "sid": "previous-local-session",
    }
    assert is_local_auth_payload(legacy_local_payload)
    assert database_user_id_from_payload(legacy_local_payload) is None
    assert not is_local_auth_payload(
        {"sub": "27", "role": "admin", "type": "access"}
    )
    assert database_user_id_from_payload(
        {"sub": "27", "role": "staff", "type": "access"}
    ) == 27
    for malformed_subject in ("admin", "٠", "0", "9" * 5000, 27, None):
        assert database_user_id_from_payload(
            {"sub": malformed_subject, "type": "access"}
        ) is None
    assert database_user_id_from_payload(["not", "claims"]) is None


def test_supabase_auth_never_falls_back_to_a_valid_local_token(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "")
    token = create_local_access_token("batch0-local-admin")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as error:
        asyncio.run(require_authenticated_user(credentials))
    assert error.value.status_code == 503


def test_supabase_rejection_does_not_fall_back_to_local_auth(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic.supabase.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-test-key")
    observed = {}

    class RejectedResponse:
        status_code = 401

    class SyntheticClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, url, headers):
            observed["url"] = url
            observed["authorization"] = headers["Authorization"]
            return RejectedResponse()

    monkeypatch.setattr("app.core.supabase_auth.httpx.AsyncClient", SyntheticClient)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="synthetic-invalid-token"
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_authenticated_user(credentials))

    assert error.value.status_code == 401
    assert observed["url"].endswith("/auth/v1/user")
    assert observed["authorization"] == "Bearer synthetic-invalid-token"


def test_missing_local_credentials_are_rejected():
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_local_staff(None))
    assert error.value.status_code == 401
