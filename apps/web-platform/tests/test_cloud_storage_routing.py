from __future__ import annotations

import hashlib

import pytest

from app.services.storage_mock import MockStorageProvider
from app.services.storage_router import (
    CLOUDINARY_DERIVATIVE_MAX_BYTES,
    SUPABASE_SOURCE_MAX_BYTES,
    StorageArtifactType,
    StorageRouter,
    UploadMetadata,
)


class StubProvider:
    def __init__(self, name: str):
        self.name = name


def metadata(size: int, artifact_type: StorageArtifactType = StorageArtifactType.SOURCE) -> UploadMetadata:
    return UploadMetadata(
        filename="sample.pdf",
        content_type="application/pdf",
        size_bytes=size,
        sha256=hashlib.sha256(b"x").hexdigest(),
        owner_id="owner-1",
        artifact_type=artifact_type,
    )


def test_source_at_50_mib_routes_to_supabase():
    router = StorageRouter({"supabase": StubProvider("supabase"), "b2": StubProvider("b2")}, provider_mode="hybrid")
    assert router.route_name(metadata(SUPABASE_SOURCE_MAX_BYTES)) == "supabase"


def test_source_over_50_mib_routes_to_b2():
    router = StorageRouter({"supabase": StubProvider("supabase"), "b2": StubProvider("b2")}, provider_mode="hybrid")
    assert router.route_name(metadata(SUPABASE_SOURCE_MAX_BYTES + 1)) == "b2"


def test_preview_below_10_mb_routes_to_cloudinary():
    router = StorageRouter({"cloudinary": StubProvider("cloudinary"), "supabase": StubProvider("supabase")}, provider_mode="hybrid")
    assert router.route_name(metadata(CLOUDINARY_DERIVATIVE_MAX_BYTES - 1, StorageArtifactType.PREVIEW)) == "cloudinary"


def test_preview_at_10_mb_is_rejected():
    router = StorageRouter({"cloudinary": StubProvider("cloudinary"), "supabase": StubProvider("supabase")}, provider_mode="hybrid")
    with pytest.raises(ValueError, match="smaller than 10 MB"):
        router.route(metadata(CLOUDINARY_DERIVATIVE_MAX_BYTES, StorageArtifactType.PREVIEW))


def test_mock_mode_requires_no_real_provider():
    mock = MockStorageProvider()
    router = StorageRouter({"mock": mock}, provider_mode="mock")
    assert router.route_name(metadata(1024)) == "mock"


def test_invalid_size_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        metadata(-1).validate()
