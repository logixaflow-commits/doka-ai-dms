import pytest

from app.core.config import settings
from app.core.local_security import create_local_access_token, decode_local_token
from app.api.routes.local_auth import LocalLogin, login


@pytest.mark.asyncio
async def test_local_login_requires_configured_password(monkeypatch):
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "")
    with pytest.raises(Exception, match="not configured"):
        await login(LocalLogin(username="admin", password="anything"))


@pytest.mark.asyncio
async def test_local_login_and_token_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    result = await login(LocalLogin(username="admin", password="local-test-password-123"))
    assert result["token_type"] == "bearer"
    payload = decode_local_token(result["access_token"])
    assert payload and payload["sub"] == "admin" and payload["role"] == "admin"
    assert decode_local_token(result["refresh_token"], expected_type="access") is None


def test_local_access_token_contains_no_password():
    token = create_local_access_token("admin")
    payload = decode_local_token(token)
    assert payload and "password" not in payload and "password_hash" not in payload
