from __future__ import annotations

import asyncio
import hashlib

from cloudflare_worker.storage_supabase import SupabaseDirectStorageProvider, SupabaseStorageConfig
from app.services.storage_router import SUPABASE_SOURCE_MAX_BYTES, UploadMetadata


def run(coro):
    return asyncio.run(coro)


def test_supabase_signed_session_contains_no_service_secret():
    calls = []

    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        return 200, {"token": "signed-upload-token"}

    provider = SupabaseDirectStorageProvider(
        SupabaseStorageConfig("https://example.supabase.co"),
        fetcher,
        auth_headers={"apikey": "publishable", "Authorization": "Bearer user-token"},
    )
    metadata = UploadMetadata("doc.pdf", "application/pdf", 1024, hashlib.sha256(b"x").hexdigest(), "owner-1")
    session = run(provider.create_upload_session(metadata))
    assert "/storage/v1/object/upload/sign/doka-documents/users/owner-1/documents/" in session.upload.url
    assert session.upload.method == "PUT"
    assert session.upload.headers["content-type"] == "application/pdf"
    assert "signed-upload-token" in session.upload.url
    assert "service" not in str(session).lower()
    assert "publishable" not in str(session).lower()
    assert "Authorization" not in str(session)
    assert calls[0][0].endswith("/object/upload/sign/doka-documents/users/owner-1/documents/" + metadata.sha256 + "/doc.pdf")


def test_supabase_boundary_accepts_exactly_50_mib():
    async def fetcher(url, **kwargs):
        return 200, {"token": "token"}

    provider = SupabaseDirectStorageProvider(SupabaseStorageConfig("https://example.supabase.co"), fetcher, auth_headers={"apikey": "k"})
    metadata = UploadMetadata("doc.pdf", "application/pdf", SUPABASE_SOURCE_MAX_BYTES, hashlib.sha256(b"x").hexdigest(), "owner-1")
    assert run(provider.create_upload_session(metadata)).provider == "supabase"


def test_supabase_rejects_over_50_mib():
    async def fetcher(url, **kwargs):
        raise AssertionError("provider must reject before network")

    provider = SupabaseDirectStorageProvider(SupabaseStorageConfig("https://example.supabase.co"), fetcher, auth_headers={"apikey": "k"})
    metadata = UploadMetadata("doc.pdf", "application/pdf", SUPABASE_SOURCE_MAX_BYTES + 1, hashlib.sha256(b"x").hexdigest(), "owner-1")
    try:
        run(provider.create_upload_session(metadata))
    except ValueError as exc:
        assert "50 MiB" in str(exc)
    else:
        raise AssertionError("expected size rejection")
