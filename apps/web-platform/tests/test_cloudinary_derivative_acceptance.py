from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "cloudinary_derivative_acceptance.py"
_SPEC = importlib.util.spec_from_file_location("doka_cloudinary_derivative_acceptance", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
ACCEPTANCE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ACCEPTANCE)

STAGING_WORKER_HOST = ACCEPTANCE.STAGING_WORKER_HOST
_assert_staging_base_url = ACCEPTANCE._assert_staging_base_url
_cleanup_cloudinary_asset = ACCEPTANCE._cleanup_cloudinary_asset
_cloudinary_signature = ACCEPTANCE._cloudinary_signature
_png_1x1 = ACCEPTANCE._png_1x1


def test_cloudinary_acceptance_runner_is_pinned_to_staging_worker():
    _assert_staging_base_url(f"https://{STAGING_WORKER_HOST}")
    with pytest.raises(SystemExit, match="exact dedicated staging Worker"):
        _assert_staging_base_url("https://doka-ai-dms.logixaflow.workers.dev")
    with pytest.raises(SystemExit, match="exact dedicated staging Worker"):
        _assert_staging_base_url("https://enterprise-ai-dms.vercel.app")


def test_cloudinary_acceptance_png_is_a_valid_minimal_png():
    payload = _png_1x1()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert payload[12:16] == b"IHDR"
    assert len(payload) < 1024


def test_cloudinary_signature_does_not_include_api_secret():
    params = {"public_id": "users/u/derivatives/thumbnail/a/thumb.png", "timestamp": "123", "type": "authenticated"}
    signature = _cloudinary_signature(params, "staging-secret")
    assert len(signature) == 64
    assert "staging-secret" not in signature


def test_cloudinary_cleanup_uses_signed_authenticated_destroy_without_logging_secret():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"result": "ok"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = _cleanup_cloudinary_asset(
            client, "staging-cloud", "staging-key", "staging-secret",
            "users/user-a/derivatives/thumbnail/hash/thumb.png",
        )
    assert result == "ok"
    request = seen[0]
    assert request.url.hostname == "api.cloudinary.com"
    assert request.url.path.endswith("/image/destroy")
    form = parse_qs(request.content.decode("utf-8"))
    assert form["type"] == ["authenticated"]
    assert form["public_id"] == ["users/user-a/derivatives/thumbnail/hash/thumb.png"]
    assert len(form["signature"][0]) == 64
    assert "staging-secret" not in request.content.decode("utf-8")
