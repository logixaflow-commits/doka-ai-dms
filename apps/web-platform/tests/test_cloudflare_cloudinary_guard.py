from __future__ import annotations

import asyncio
import hashlib

from cloudflare_worker.storage_cloudinary import CloudinaryConfig, CloudinaryCreditGuard, CloudinaryDerivativeProvider
from storage_contracts_compat import CLOUDINARY_DERIVATIVE_MAX_BYTES, StorageArtifactType, UploadMetadata


def run(coro):
    return asyncio.run(coro)


def test_healthy_credits_allows_cloudinary():
    async def fetcher(url, **kwargs):
        return 200, {"credits": {"usage": 10, "limit": 25}}
    p = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret", 5), fetcher)
    meta = UploadMetadata("thumb.jpg", "image/jpeg", 1024, hashlib.sha256(b"x").hexdigest(), "owner", StorageArtifactType.THUMBNAIL)
    session = run(p.create_upload_session(meta))
    assert session.provider == "cloudinary"
    assert "secret" not in str(session)
    assert "secret" not in session.upload.fields.values()


def test_low_credits_falls_back_with_stable_warning():
    async def fetcher(url, **kwargs):
        return 200, {"credits": {"usage": 21, "limit": 25}}
    p = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret", 5), fetcher)
    meta = UploadMetadata("thumb.jpg", "image/jpeg", 1024, hashlib.sha256(b"x").hexdigest(), "owner", StorageArtifactType.THUMBNAIL)
    try:
        run(p.create_upload_session(meta))
    except RuntimeError as exc:
        assert str(exc) == "cloudinary_credit_fallback"
    else:
        raise AssertionError("expected low-credit fallback")


def test_unknown_usage_fails_closed_without_leaking_credentials():
    async def fetcher(url, **kwargs):
        return 500, {"api_secret": "should-not-leak"}
    guard = CloudinaryCreditGuard(CloudinaryConfig("cloud", "key", "secret"), fetcher)
    decision = run(guard.check())
    assert not decision.allowed
    assert decision.warning == "cloudinary_usage_unknown"
    assert "secret" not in str(decision)


def test_cloudinary_10mb_boundary_rejected():
    async def fetcher(url, **kwargs):
        return 200, {"credits": {"usage": 1, "limit": 25}}
    p = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret"), fetcher)
    meta = UploadMetadata("thumb.jpg", "image/jpeg", CLOUDINARY_DERIVATIVE_MAX_BYTES, hashlib.sha256(b"x").hexdigest(), "owner", StorageArtifactType.THUMBNAIL)
    try:
        run(p.create_upload_session(meta))
    except ValueError as exc:
        assert "10 MB" in str(exc)
    else:
        raise AssertionError("expected size rejection")



def test_cloudinary_derivatives_are_owner_scoped_authenticated_and_time_limited():
    from urllib.parse import parse_qs, urlparse

    async def fetcher(url, **kwargs):
        return 200, {"credits": {"usage": 10, "limit": 25}}

    provider = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret", 5), fetcher)
    payload = b"x" * 1024
    digest = hashlib.sha256(payload).hexdigest()
    metadata = UploadMetadata("thumb.jpg", "image/jpeg", len(payload), digest, "user-a", StorageArtifactType.THUMBNAIL)
    session = run(provider.create_upload_session(metadata))

    public_id = session.upload.fields["public_id"]
    assert public_id.startswith("users/user-a/derivatives/thumbnail/")
    assert session.upload.fields["type"] == "authenticated"
    assert f"size_bytes={len(payload)}" in session.upload.fields["context"]
    assert "content_type=image/jpeg" in session.upload.fields["context"]
    assert "secret" not in str(session.upload.fields.values())

    signed_url = run(provider.get_signed_download(session.object_ref, expires_seconds=120))
    parsed = urlparse(signed_url)
    query = parse_qs(parsed.query)
    assert parsed.hostname == "api.cloudinary.com"
    assert parsed.path.endswith("/image/download")
    assert query["type"] == ["authenticated"]
    assert query["public_id"] == [public_id]
    assert int(query["expires_at"][0]) > int(query["timestamp"][0])
    assert int(query["expires_at"][0]) - int(query["timestamp"][0]) == 120
    assert query["api_key"] == ["key"]
    assert query["signature"] and len(query["signature"][0]) == 64
    assert "secret" not in signed_url


def test_cloudinary_completion_verifies_actual_downloaded_bytes():
    from urllib.parse import parse_qs, urlparse

    payload = b"verified-thumbnail" * 32
    digest = hashlib.sha256(payload).hexdigest()
    expected_size = len(payload)

    async def fetcher(url, **kwargs):
        if url.endswith("/usage"):
            return 200, {"credits": {"usage": 1, "limit": 25}}
        if kwargs.get("return_sha256"):
            return 200, {"sha256": digest, "size_bytes": expected_size}
        return 404, {}

    provider = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret"), fetcher)
    metadata = UploadMetadata("thumb.png", "image/png", expected_size, digest, "user-a", StorageArtifactType.THUMBNAIL)
    session = run(provider.create_upload_session(metadata))
    result = run(provider.complete_upload(session, {
        "public_id": session.upload.fields["public_id"],
        "type": "authenticated",
        "resource_type": "image",
        "bytes": expected_size,
        "context": {"custom": {"sha256": digest, "size_bytes": str(expected_size), "content_type": "image/png"}},
    }))
    assert result.size_bytes == expected_size
    assert result.sha256 == digest
    assert result.content_type == "image/png"


def test_cloudinary_completion_rejects_public_delivery_type_and_hash_mismatch():
    payload = b"verified-thumbnail" * 32
    digest = hashlib.sha256(payload).hexdigest()
    expected_size = len(payload)

    async def fetcher(url, **kwargs):
        if url.endswith("/usage"):
            return 200, {"credits": {"usage": 1, "limit": 25}}
        if kwargs.get("return_sha256"):
            return 200, {"sha256": hashlib.sha256(b"tampered").hexdigest(), "size_bytes": expected_size}
        return 404, {}

    provider = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret"), fetcher)
    metadata = UploadMetadata("thumb.png", "image/png", expected_size, digest, "user-a", StorageArtifactType.THUMBNAIL)
    session = run(provider.create_upload_session(metadata))
    result = {
        "public_id": session.upload.fields["public_id"],
        "type": "upload",
        "resource_type": "image",
        "bytes": expected_size,
        "context": session.upload.fields["context"],
    }
    try:
        run(provider.complete_upload(session, result))
    except ValueError as exc:
        assert "authenticated delivery" in str(exc)
    else:
        raise AssertionError("expected public delivery type to be rejected")

    result["type"] = "authenticated"
    try:
        run(provider.complete_upload(session, result))
    except ValueError as exc:
        assert "content integrity" in str(exc)
    else:
        raise AssertionError("expected mismatched remote bytes to be rejected")


def test_cloudinary_signed_download_rejects_cross_owner_object_key():
    async def fetcher(url, **kwargs):
        return 200, {"credits": {"usage": 1, "limit": 25}}

    provider = CloudinaryDerivativeProvider(CloudinaryConfig("cloud", "key", "secret"), fetcher)
    from storage_contracts_compat import StorageObjectRef
    ref = StorageObjectRef("cloudinary", "users/user-b/derivatives/thumbnail/hash/thumb.png", "user-a")
    try:
        run(provider.get_signed_download(ref))
    except ValueError as exc:
        assert "authenticated owner" in str(exc)
    else:
        raise AssertionError("expected cross-owner key to be rejected")
