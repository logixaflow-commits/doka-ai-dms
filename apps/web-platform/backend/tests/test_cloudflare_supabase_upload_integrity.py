import hashlib
import sys
from pathlib import Path

import pytest

WORKER_DIR = Path(__file__).resolve().parents[1] / "cloudflare_worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from shared.storage_contracts import SignedUpload, StorageObjectRef, UploadSession
from storage_supabase import SupabaseDirectStorageProvider, SupabaseStorageConfig


@pytest.mark.asyncio
async def test_supabase_completion_accepts_matching_stored_content():
    body = b"verified document bytes"
    digest = hashlib.sha256(body).hexdigest()
    provider = _provider(body, digest)

    stored = await provider.complete_upload(_session(), {"size_bytes": len(body), "sha256": digest})

    assert stored.size_bytes == len(body)
    assert stored.sha256 == digest


@pytest.mark.asyncio
async def test_supabase_completion_rejects_wrong_stored_content_hash():
    body = b"actual stored bytes"
    expected = hashlib.sha256(b"expected bytes").hexdigest()
    provider = _provider(body, hashlib.sha256(body).hexdigest())

    with pytest.raises(ValueError, match="content SHA-256"):
        await provider.complete_upload(_session(), {"size_bytes": len(body), "sha256": expected})


@pytest.mark.asyncio
async def test_supabase_completion_rejects_wrong_stored_content_size():
    body = b"actual stored bytes"
    digest = hashlib.sha256(body).hexdigest()
    provider = _provider(body, digest)

    with pytest.raises(ValueError, match="content size"):
        await provider.complete_upload(_session(), {"size_bytes": len(body) + 1, "sha256": digest})


def _session():
    ref = StorageObjectRef("supabase", "users/user-1/documents/file.bin", "user-1")
    return UploadSession(
        provider="supabase",
        object_ref=ref,
        expires_at=9999999999,
        upload=SignedUpload(method="PUT", url="https://example.invalid/upload"),
        session_id="test-session",
    )


def _provider(body: bytes, stored_digest: str):
    async def fetcher(url, *, method="GET", headers=None, body=None, return_headers=False,
                      return_sha256=False, max_bytes=50 * 1024 * 1024):
        if "/object/info/" in url:
            return 200, {"size": len(_body), "contentType": "application/octet-stream"}
        if "/object/authenticated/" in url and return_sha256:
            return 200, {"size_bytes": len(_body), "sha256": _digest}
        raise AssertionError(f"Unexpected storage request: {method} {url}")

    _body = body
    _digest = stored_digest
    return SupabaseDirectStorageProvider(
        SupabaseStorageConfig(base_url="https://supabase.example", bucket="doka-documents"),
        fetcher,
        auth_headers={"Authorization": "Bearer test-token"},
    )
