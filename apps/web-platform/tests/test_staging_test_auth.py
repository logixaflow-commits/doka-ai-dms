from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "staging_test_auth.py"
_SPEC = importlib.util.spec_from_file_location("doka_staging_test_auth", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
AUTH = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(AUTH)


def test_staging_auth_mints_token_only_from_exact_staging_project():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": "a" * 120 + ".b" * 2 + ".c" * 2,
                "expires_in": 3600,
                "user": {"id": "staging-user-a"},
            },
        )

    with httpx.Client(
        base_url=AUTH.STAGING_SUPABASE_URL,
        transport=httpx.MockTransport(handler),
    ) as client:
        token, user_id = AUTH._request_access_token(client, "a@example.test", "password-a", "sb_publishable_test")

    assert user_id == "staging-user-a"
    assert token.startswith("a" * 120)
    assert len(seen) == 1
    assert seen[0].url.host == AUTH.STAGING_SUPABASE_HOST
    assert seen[0].url.path == "/auth/v1/token"
    assert seen[0].headers["apikey"] == "sb_publishable_test"
    assert b'"email":"a@example.test"' in seen[0].content


def test_staging_auth_refuses_production_supabase_before_network():
    with httpx.Client(base_url="https://jkobgssaqifzrqfirdfu.supabase.co") as client:
        with pytest.raises(SystemExit, match="exact staging Supabase project"):
            AUTH._request_access_token(client, "a@example.test", "password-a", "key")


def test_staging_auth_does_not_echo_auth_response_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "bad password", "email": "private@example.test"})

    with httpx.Client(
        base_url=AUTH.STAGING_SUPABASE_URL,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(SystemExit, match="HTTP 400") as exc:
            AUTH._request_access_token(client, "private@example.test", "bad-password", "key")
    assert "bad password" not in str(exc.value)
    assert "private@example.test" not in str(exc.value)


def test_provider_and_isolation_wrappers_are_staging_only():
    root = Path(__file__).resolve().parents[3]
    provider = (root / "scripts" / "run-cloud-provider-acceptance.ps1").read_text(encoding="utf-8")
    isolation = (root / "scripts" / "run-cloud-isolation-acceptance.ps1").read_text(encoding="utf-8")
    assert '[string]$BaseUrl = "https://doka-ai-dms-staging.logixaflow.workers.dev"' in provider
    assert '$parsed.Host -ne "doka-ai-dms-staging.logixaflow.workers.dev"' in provider
    assert '$parsed.Host -ne "doka-ai-dms-staging.logixaflow.workers.dev"' in isolation
