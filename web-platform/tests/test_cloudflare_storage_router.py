from __future__ import annotations

import asyncio
import hashlib

from cloudflare_worker.storage_router import CloudStorageRouter
from cloudflare_worker.storage_contracts_compat import StorageArtifactType, UploadMetadata


class Provider:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.calls = 0
    async def create_upload_session(self, metadata):
        self.calls += 1
        if self.fail:
            raise RuntimeError("cloudinary_credit_fallback")
        return {"provider": self.name}


def run(coro):
    return asyncio.run(coro)


def meta(kind=StorageArtifactType.SOURCE, size=1):
    return UploadMetadata("doc.pdf", "application/pdf", size, hashlib.sha256(b"x").hexdigest(), "owner", kind)


def test_source_routes_supabase_or_b2():
    s, b = Provider("supabase"), Provider("b2")
    router = CloudStorageRouter(supabase=s, b2=b, mode="hybrid")
    p, d = run(router.select(meta(size=50*1024*1024)))
    assert p is s and d.provider == "supabase"
    p, d = run(router.select(meta(size=50*1024*1024+1)))
    assert p is b and d.provider == "b2"


def test_cloudinary_failure_falls_back_to_supabase():
    s, c = Provider("supabase"), Provider("cloudinary", fail=True)
    router = CloudStorageRouter(supabase=s, cloudinary=c, mode="hybrid")
    session, decision = run(router.create_upload_session(meta(StorageArtifactType.PREVIEW)))
    assert session["provider"] == "supabase"
    assert decision.provider == "supabase"
    assert decision.warnings == ("cloudinary_credit_fallback",)


def test_mock_mode_uses_only_mock_provider():
    m, s = Provider("mock"), Provider("supabase")
    router = CloudStorageRouter(supabase=s, mock=m, mode="mock")
    session, decision = run(router.create_upload_session(meta()))
    assert session["provider"] == "mock"
    assert decision.provider == "mock"
    assert s.calls == 0
