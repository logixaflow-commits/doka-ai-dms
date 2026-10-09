from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

_MODULE_SPEC = importlib.util.spec_from_file_location(
    "doka_cloud_acceptance",
    Path(__file__).resolve().parents[2] / "scripts" / "cloud_acceptance.py",
)
assert _MODULE_SPEC is not None and _MODULE_SPEC.loader is not None
DOKA_CLOUD_ACCEPTANCE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(DOKA_CLOUD_ACCEPTANCE)

_download_and_verify = DOKA_CLOUD_ACCEPTANCE._download_and_verify
_upload_document = DOKA_CLOUD_ACCEPTANCE._upload_document


def test_upload_uses_signed_provider_url_and_worker_completion():
    payload = b"signed direct upload acceptance"
    digest = hashlib.sha256(payload).hexdigest()
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host + request.url.path)
        if request.url.path == "/api/storage/upload-session":
            assert request.headers.get("authorization") == "Bearer user-token"
            body = json.loads(request.content)
            assert body["sha256"] == digest
            assert body["size_bytes"] == len(payload)
            return httpx.Response(
                200,
                json={
                    "session_id": "signed-session-token",
                    "provider": "supabase",
                    "upload": {
                        "method": "PUT",
                        "url": "https://storage.example/signed-upload",
                        "headers": {"content-type": "text/plain"},
                        "fields": {},
                    },
                },
            )
        if request.url.host == "storage.example":
            assert request.method == "PUT"
            assert request.content == payload
            assert "authorization" not in request.headers
            return httpx.Response(200)
        if request.url.path == "/api/storage/upload-complete":
            assert request.headers.get("authorization") == "Bearer user-token"
            body = json.loads(request.content)
            assert body["session_id"] == "signed-session-token"
            assert body["sha256"] == digest
            assert body["provider_result"] == {}
            return httpx.Response(
                200,
                json={
                    "document": {
                        "id": "document-123",
                        "sha256": digest,
                        "size_bytes": len(payload),
                        "storage_status": "ready",
                    },
                    "warnings": [],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client:
        document = _upload_document(client, "user-token", payload, "acceptance.txt", "text/plain")

    assert document["id"] == "document-123"
    assert seen == [
        "cloud.example/api/storage/upload-session",
        "storage.example/signed-upload",
        "cloud.example/api/storage/upload-complete",
    ]


def test_download_integrity_hashes_actual_downloaded_bytes():
    payload = b"actual object bytes"
    digest = hashlib.sha256(payload).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/documents/doc-1/download":
            assert request.headers.get("authorization") == "Bearer user-token"
            return httpx.Response(
                200,
                json={"url": "https://storage.example/signed-download", "sha256": digest},
            )
        if request.url.host == "storage.example":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=payload)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client:
        _download_and_verify(client, "user-token", "doc-1", digest)


def test_upload_rejects_non_https_signed_provider_url():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "session_id": "signed-session-token",
                "provider": "supabase",
                "upload": {"method": "PUT", "url": "http://storage.example/upload"},
            },
        )

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client, pytest.raises(AssertionError, match="safe HTTPS URL"):
        _upload_document(client, "user-token", b"x", "acceptance.txt", "text/plain")
