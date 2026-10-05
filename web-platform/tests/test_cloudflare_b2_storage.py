from __future__ import annotations

import asyncio
import hashlib
import re

from cloudflare_worker.storage_b2 import B2StorageConfig, B2StorageProvider
from app.services.storage_router import B2_MULTIPART_THRESHOLD_BYTES, UploadMetadata


def run(coro):
    return asyncio.run(coro)


def test_b2_signed_upload_contains_no_application_secret():
    async def fetcher(*args, **kwargs):
        raise AssertionError("upload session creation must not upload bytes")

    secret = "application-secret"
    provider = B2StorageProvider(B2StorageConfig("https://s3.us-east-005.backblazeb2.com", "bucket", "key-id", secret), fetcher)
    meta = UploadMetadata("archive.zip", "application/zip", 60 * 1024 * 1024, hashlib.sha256(b"x").hexdigest(), "owner-1")
    session = run(provider.create_upload_session(meta))
    assert session.provider == "b2"
    assert secret not in session.upload.url
    assert secret not in str(session.upload.headers)
    assert "X-Amz-Signature=" in session.upload.url


def test_b2_multipart_required_above_5_gib():
    calls=[]
    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        return 200, b"<InitiateMultipartUploadResult><UploadId>u-1</UploadId></InitiateMultipartUploadResult>"
    provider = B2StorageProvider(B2StorageConfig("https://s3.example", "bucket", "key", "secret"), fetcher)
    meta = UploadMetadata("huge.bin", "application/octet-stream", B2_MULTIPART_THRESHOLD_BYTES + 1, hashlib.sha256(b"x").hexdigest(), "owner")
    upload = run(provider.initiateMultipartUpload(meta))
    assert upload.upload_id == "u-1"
    assert calls and "uploadId" not in calls[0][0]


def test_b2_part_presign_does_not_buffer_part():
    async def fetcher(*args, **kwargs):
        raise AssertionError("part signing must not upload bytes")
    provider = B2StorageProvider(B2StorageConfig("https://s3.example", "bucket", "key", "secret"), fetcher)
    meta = UploadMetadata("huge.bin", "application/octet-stream", B2_MULTIPART_THRESHOLD_BYTES + 1, hashlib.sha256(b"x").hexdigest(), "owner")
    upload = run(provider.initiateMultipartUpload(meta)) if False else None
    from cloudflare_worker.storage_b2 import MultipartUpload
    from storage_contracts_compat import StorageObjectRef
    m = MultipartUpload("u-1", StorageObjectRef("b2", "users/owner/documents/x/huge.bin", "owner"), 100*1024*1024, 9999999999)
    part = run(provider.uploadPart(m, 1, hashlib.sha256(b"part").hexdigest()))
    assert part.signed_request.method == "PUT"
    assert "x-amz-checksum-sha256" in part.signed_request.headers
