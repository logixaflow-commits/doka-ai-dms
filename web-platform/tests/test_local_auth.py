import json
import importlib
import sqlite3
import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import settings
from app.core.local_security import create_local_access_token, decode_local_token, clear_login_failures
import app.core.local_security as local_security
from app.api.routes.local_auth import LocalLogin, LocalRefresh, login, logout, me, refresh
from app.core.supabase_auth import _supabase_configured, require_local_workspace_user


def _request(host: str = "127.0.0.1") -> Request:
    return Request({"type": "http", "headers": [], "client": (host, 12345)})


@pytest.fixture(autouse=True)
def isolate_local_auth_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3")



@pytest.mark.asyncio
async def test_local_login_requires_configured_password(monkeypatch):
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "")
    with pytest.raises(Exception, match="not configured"):
        await login(LocalLogin(username="admin", password="anything"), _request())


@pytest.mark.asyncio
async def test_local_login_and_token_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    result = await login(LocalLogin(username="admin", password="local-test-password-123"), _request())
    assert result["token_type"] == "bearer"
    payload = decode_local_token(result["access_token"])
    assert payload and payload["sub"] == "admin" and payload["role"] == "admin"
    assert decode_local_token(result["refresh_token"], expected_type="access") is None


def test_local_access_token_contains_no_password():
    token = create_local_access_token("admin")
    payload = decode_local_token(token)
    assert payload and "password" not in payload and "password_hash" not in payload


@pytest.mark.asyncio
async def test_local_login_lockout_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    monkeypatch.setattr(settings, "MAX_LOGIN_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "LOCKOUT_DURATION_MINUTES", 30)
    clear_login_failures("admin", "127.0.0.1")

    request = _request()

    for _ in range(3):
        with pytest.raises(Exception, match="Invalid username or password"):
            await login(LocalLogin(username="admin", password="wrong"), request)

    with pytest.raises(Exception, match="Too many failed login attempts"):
        await login(LocalLogin(username="admin", password="local-test-password-123"), request)

    clear_login_failures("admin", "127.0.0.1")



def test_placeholder_supabase_credentials_do_not_disable_local_auth(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://your-project-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_your_public_key")
    assert _supabase_configured() is False


def test_real_supabase_configuration_is_detected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_example")
    assert _supabase_configured() is True



@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
async def test_filesystem_workspace_api_is_disabled_outside_local_environments(monkeypatch, environment):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    with pytest.raises(HTTPException) as error:
        await require_local_workspace_user(None)
    assert error.value.status_code == 404



@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
async def test_local_password_login_is_disabled_outside_local_environments(monkeypatch, environment):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    with pytest.raises(HTTPException) as error:
        await login(LocalLogin(username="admin", password="irrelevant"), _request())
    assert error.value.status_code == 404



@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
async def test_local_refresh_identity_and_logout_are_disabled_outside_local_environments(monkeypatch, environment):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)

    with pytest.raises(HTTPException) as refresh_error:
        await refresh(LocalRefresh(refresh_token="not-a-valid-token"))
    assert refresh_error.value.status_code == 404

    with pytest.raises(HTTPException) as identity_error:
        await me(_request())
    assert identity_error.value.status_code == 404

    with pytest.raises(HTTPException) as logout_error:
        await logout(_request())
    assert logout_error.value.status_code == 404


@pytest.mark.asyncio
async def test_local_refresh_token_is_single_use_and_rotates(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    clear_login_failures("admin", "127.0.0.1")

    initial = await login(
        LocalLogin(username="admin", password="local-test-password-123"),
        _request(),
    )
    rotated = await refresh(LocalRefresh(refresh_token=initial["refresh_token"]))
    initial_access = decode_local_token(initial["access_token"])
    rotated_access = decode_local_token(rotated["access_token"])
    assert initial_access and rotated_access
    assert initial_access["sid"] == rotated_access["sid"]
    assert decode_local_token(rotated["refresh_token"], expected_type="refresh")

    with pytest.raises(HTTPException) as error:
        await refresh(LocalRefresh(refresh_token=initial["refresh_token"]))
    assert error.value.status_code == 401



@pytest.mark.asyncio
async def test_local_logout_invalidates_access_and_refresh_tokens(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    result = await login(
        LocalLogin(username="admin", password="local-test-password-123"),
        _request(),
    )
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/logout",
        "query_string": b"",
        "headers": [(b"authorization", f"Bearer {result['access_token']}".encode())],
        "client": ("127.0.0.1", 12345),
    }
    body = json.dumps({"refresh_token": result["refresh_token"]}).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(scope, receive)
    response = await logout(request)

    assert response["message"] == "Local session ended."
    assert decode_local_token(result["access_token"]) is None
    assert decode_local_token(result["refresh_token"], expected_type="refresh") is None
    refresh_claims = jwt.decode(
        result["refresh_token"], settings.SECRET_KEY, algorithms=["HS256"]
    )
    with sqlite3.connect(settings.LOCAL_AUTH_STATE_PATH) as connection:
        revoked_until = connection.execute(
            "SELECT expires_at FROM local_token_state WHERE token_id = ?",
            (f"sid:{refresh_claims['sid']}",),
        ).fetchone()[0]
    assert revoked_until >= float(refresh_claims["exp"])



@pytest.mark.asyncio
async def test_logout_revokes_rotated_session_tokens_across_module_restart(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    initial = await login(
        LocalLogin(username="admin", password="local-test-password-123"),
        _request(),
    )
    rotated = await refresh(LocalRefresh(refresh_token=initial["refresh_token"]))

    assert decode_local_token(rotated["access_token"])
    assert local_security.invalidate_local_token(initial["access_token"])

    # Reload the module to model a backend process restart; SQLite state must survive.
    importlib.reload(local_security)
    assert local_security.decode_local_token(rotated["access_token"]) is None
    assert local_security.decode_local_token(
        rotated["refresh_token"], expected_type="refresh"
    ) is None


@pytest.mark.asyncio
async def test_refresh_replay_remains_blocked_after_module_restart(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    initial = await login(
        LocalLogin(username="admin", password="local-test-password-123"),
        _request(),
    )

    assert local_security.consume_local_refresh_token(initial["refresh_token"])
    importlib.reload(local_security)
    assert local_security.consume_local_refresh_token(initial["refresh_token"]) is None
