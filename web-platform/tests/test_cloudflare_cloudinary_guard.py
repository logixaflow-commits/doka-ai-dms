from __future__ import annotations

import asyncio
import hashlib

from cloudflare_worker.storage_cloudinary import CloudinaryConfig, CloudinaryCreditGuard, CloudinaryDerivativeProvider
from cloudflare_worker.storage_contracts_compat import CLOUDINARY_DERIVATIVE_MAX_BYTES, StorageArtifactType, UploadMetadata


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
