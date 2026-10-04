import json
import importlib
import io
import sqlite3
from datetime import datetime, timedelta, timezone
import httpx
import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from loguru import logger
from starlette.requests import Request

from app.core.config import settings
from app.core.local_security import create_local_access_token, decode_local_token, clear_login_failures
import app.core.local_security as local_security
import app.core.supabase_auth as supabase_auth
from app.api.routes import workspace
from app.api.routes.local_auth import router as local_auth_router
from app.api.routes.local_auth import LocalLogin, LocalRefresh, login, logout, me, refresh
from app.core.supabase_auth import _supabase_configured, require_local_workspace_user


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _request(host: str = "127.0.0.1") -> Request:
    return Request({"type": "http", "headers": [], "client": (host, 12345)})


@pytest.fixture(autouse=True)
def isolate_local_auth_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3")



@pytest.mark.asyncio
async def test_local_login_requires_configured_password(monkeypatch):
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "")
    with pytest.raises(HTTPException, match="not configured") as error:
        await login(LocalLogin(username="admin", password="anything"), _request())
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_local_login_and_token_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "local-test-password-123")
    result = await login(LocalLogin(username="admin", password="local-test-password-123"), _request())
    assert result["token_type"] == "bearer"
    payload = decode_local_token(result["access_token"])
    assert payload and payload["sub"] == "admin" and payload["role"] == "admin"
    assert decode_local_token(result["refresh_token"], expected_type="access") is None


@pytest.mark.parametrize(
    "password",
    [
        "ASCII-password-42",
        "\u1019\u103c\u1014\u103a\u1019\u102c-password-42",
        "Mixed-\u1019\u103c\u1014\u103a\u1019\u102c-password-42",
        "Caf\u00e9-password-42",
        " password-with-boundary-spaces-42 ",
        "Emoji-\U0001f512-password-42",
        "\u1019" * 12,
        "\u1019" * 25,
    ],
)
def test_local_login_accepts_exact_ascii_and_unicode_passwords(
    tmp_path, monkeypatch, password
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-unicode-user")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", password)
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3")

    app = FastAPI()
    app.include_router(local_auth_router, prefix="/api/auth")
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "synthetic-unicode-user", "password": password},
        )

    assert response.status_code == 200
    assert decode_local_token(response.json()["access_token"])["sub"] == "synthetic-unicode-user"


def test_local_login_rejects_malformed_request_without_disclosing_password(
    tmp_path, monkeypatch
):
    configured_password = "Synthetic-configured-password-42"
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-unicode-user")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", configured_password)
    monkeypatch.setattr(
        settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3"
    )

    app = FastAPI()
    app.include_router(local_auth_router, prefix="/api/auth")
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            content=b"{",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 422
    assert configured_password not in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


@pytest.mark.asyncio
async def test_local_login_does_not_trim_password_whitespace(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-space-user")
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", " password-with-spaces-42 "
    )
    clear_login_failures("synthetic-space-user", "127.0.0.1")

    with pytest.raises(HTTPException) as error:
        await login(
            LocalLogin(
                username="synthetic-space-user",
                password="password-with-spaces-42",
            ),
            _request(),
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid username or password."
    clear_login_failures("synthetic-space-user", "127.0.0.1")


def test_local_login_unicode_mismatch_does_not_disclose_credentials(
    tmp_path, monkeypatch
):
    configured_password = "Expected-\u1019\u103c\u1014\u103a\u1019\u102c-42"
    submitted_password = "Submitted-\u1019\u103c\u1014\u103a\u1019\u102c-42"
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-unicode-user")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", configured_password)
    monkeypatch.setattr(
        settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3"
    )

    app = FastAPI()
    app.include_router(local_auth_router, prefix="/api/auth")
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "synthetic-unicode-user",
                "password": submitted_password,
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password."}
    assert configured_password not in response.text
    assert submitted_password not in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


@pytest.mark.asyncio
async def test_local_login_rejects_unicode_password_mismatch(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-unicode-user")
    monkeypatch.setattr(
        settings,
        "BOOTSTRAP_ADMIN_PASSWORD",
        "Cafe\u0301-password-42",
    )
    clear_login_failures("synthetic-unicode-user", "127.0.0.1")

    with pytest.raises(HTTPException) as error:
        await login(
            LocalLogin(
                username="synthetic-unicode-user",
                password="Caf\u00e9-password-42",
            ),
            _request(),
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid username or password."
    assert "Cafe" not in error.value.detail
    clear_login_failures("synthetic-unicode-user", "127.0.0.1")


@pytest.mark.asyncio
async def test_local_login_rejects_invalid_unicode_scalar_as_bad_credentials(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-unicode-user")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "synthetic-password-42")
    clear_login_failures("synthetic-unicode-user", "127.0.0.1")

    with pytest.raises(HTTPException) as error:
        await login(
            LocalLogin(
                username="synthetic-unicode-user",
                password="synthetic-password-\ud800",
            ),
            _request(),
        )

    assert error.value.status_code == 401
    clear_login_failures("synthetic-unicode-user", "127.0.0.1")


@pytest.mark.asyncio
async def test_local_login_does_not_truncate_long_utf8_password_or_store_or_log_it(
    tmp_path, monkeypatch
):
    password = "\u1019" * 25
    different_password = ("\u1019" * 24) + "\u1018"
    database_path = tmp_path / "local-auth.sqlite3"
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "synthetic-long-password-user")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", password)
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", database_path)
    clear_login_failures("synthetic-long-password-user", "127.0.0.1")
    log_stream = io.StringIO()
    sink_id = logger.add(log_stream, level="DEBUG")
    try:
        result = await login(
            LocalLogin(username="synthetic-long-password-user", password=password),
            _request(),
        )
        with pytest.raises(HTTPException) as error:
            await login(
                LocalLogin(
                    username="synthetic-long-password-user",
                    password=different_password,
                ),
                _request(),
            )
    finally:
        logger.remove(sink_id)
        clear_login_failures("synthetic-long-password-user", "127.0.0.1")

    assert error.value.status_code == 401
    assert password.encode("utf-8") not in database_path.read_bytes()
    assert password not in log_stream.getvalue()
    assert password not in result["access_token"]


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
async def test_local_workspace_rejects_anonymous_invalid_and_expired_tokens(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "type": "access",
            "jti": "expired-token",
            "sid": "expired-session",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    for credentials in (None, _credentials("invalid-local-token"), _credentials(expired_token)):
        with pytest.raises(HTTPException) as error:
            await require_local_workspace_user(credentials)
        assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_local_workspace_accepts_valid_local_token_without_supabase(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    token = create_local_access_token("local-admin")

    assert await require_local_workspace_user(_credentials(token)) == "local-admin"


@pytest.mark.asyncio
async def test_local_workspace_remains_available_when_supabase_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")
    calls = []

    class UnavailableClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            calls.append(url)
            raise httpx.ConnectError("Synthetic Supabase outage")

    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", UnavailableClient)
    token = create_local_access_token("local-admin")

    assert await require_local_workspace_user(_credentials(token)) == "local-admin"
    assert calls == []


@pytest.mark.asyncio
async def test_local_workspace_never_accepts_supabase_identity_or_calls_supabase(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")
    calls = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "synthetic-cloud-user"}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            calls.append(url)
            return FakeResponse()

    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", FakeClient)

    with pytest.raises(HTTPException) as error:
        await require_local_workspace_user(_credentials("synthetic-supabase-token"))
    assert error.value.status_code == 401
    assert calls == []

    now = datetime.now(timezone.utc)
    cloud_token = jwt.encode(
        {
            "sub": "synthetic-cloud-user",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": "https://synthetic-project.invalid/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as cloud_token_error:
        await require_local_workspace_user(_credentials(cloud_token))
    assert cloud_token_error.value.status_code == 401
    assert calls == []

    local_token = create_local_access_token("local-admin")
    assert await require_local_workspace_user(_credentials(local_token)) == "local-admin"
    assert calls == []


def test_protected_local_workspace_route_rejects_anonymous_and_accepts_local_token(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "WORKING_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(settings, "SOURCE_ROOT", tmp_path / "source")
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "local-auth.sqlite3")
    app = FastAPI()
    app.include_router(workspace.router)
    from app.api.routes.workspace_files import router as workspace_files_router

    app.include_router(workspace_files_router)
    token = create_local_access_token("local-admin")

    with TestClient(app) as client:
        anonymous = client.get("/api/workspace/imports")
        assert anonymous.status_code == 401
        anonymous_file = client.get(
            f"/api/workspace/imports/{'a' * 32}/files/synthetic.txt"
        )
        assert anonymous_file.status_code == 401

        forged_identity = client.get(
            "/api/workspace/imports",
            headers={
                "X-User-ID": "forged-admin",
                "X-Username": "forged-admin",
                "X-User-Role": "admin",
            },
        )
        assert forged_identity.status_code == 401

        invalid = client.get(
            "/api/workspace/imports",
            headers={"Authorization": "Bearer invalid-local-token"},
        )
        assert invalid.status_code == 401

        authenticated = client.get(
            "/api/workspace/imports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert authenticated.status_code == 200
        assert authenticated.json() == {"imports": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
async def test_local_password_login_is_disabled_outside_local_environments(monkeypatch, environment):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    with pytest.raises(HTTPException) as error:
        await login(LocalLogin(username="admin", password="irrelevant"), _request())
    assert error.value.status_code == 404



@pytest.mark.asyncio
async def test_cloud_auth_uses_supabase_identity_with_synthetic_mock(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "synthetic-cloud-user"}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            assert url == "https://synthetic-project.invalid/auth/v1/user"
            assert headers["apikey"] == "synthetic-publishable-key"
            assert headers["Authorization"] == "Bearer synthetic-cloud-token"
            return FakeResponse()

    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", FakeClient)

    from app.core.supabase_auth import require_authenticated_user

    assert (
        await require_authenticated_user(_credentials("synthetic-cloud-token"))
        == "synthetic-cloud-user"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["production", "staging", "prod"])
async def test_cloud_auth_without_supabase_configuration_fails_closed(
    monkeypatch, environment
):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    token = create_local_access_token("synthetic-local-admin")

    from app.core.supabase_auth import require_authenticated_user

    with pytest.raises(HTTPException) as error:
        await require_authenticated_user(_credentials(token))
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["development", "local", "test"])
async def test_cloud_auth_without_supabase_rejects_local_token_in_every_environment(
    monkeypatch, environment
):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    token = create_local_access_token("synthetic-local-admin")

    from app.core.supabase_auth import require_authenticated_user

    with pytest.raises(HTTPException) as error:
        await require_authenticated_user(_credentials(token))

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_cloud_auth_rejects_local_token_when_supabase_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")

    class UnauthorizedResponse:
        status_code = 401

        @staticmethod
        def json():
            return {"message": "synthetic rejection"}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            return UnauthorizedResponse()

    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", FakeClient)
    token = create_local_access_token("synthetic-local-admin")

    from app.core.supabase_auth import require_authenticated_user

    with pytest.raises(HTTPException) as error:
        await require_authenticated_user(_credentials(token))

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_cloud_auth_fails_closed_when_supabase_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setenv("SUPABASE_URL", "https://synthetic-project.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")

    class UnavailableClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers):
            raise httpx.ConnectError("synthetic Supabase outage")

    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", UnavailableClient)
    token = create_local_access_token("synthetic-local-admin")

    from app.core.supabase_auth import require_authenticated_user

    with pytest.raises(HTTPException) as error:
        await require_authenticated_user(_credentials(token))

    assert error.value.status_code == 503


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
