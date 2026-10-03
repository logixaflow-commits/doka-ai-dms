import pytest
from starlette.requests import Request

from app.core.config import settings
from app.core.local_security import create_local_access_token, decode_local_token, clear_login_failures
from app.api.routes.local_auth import LocalLogin, login
from app.core.supabase_auth import _supabase_configured


def _request(host: str = "127.0.0.1") -> Request:
    return Request({"type": "http", "headers": [], "client": (host, 12345)})



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
