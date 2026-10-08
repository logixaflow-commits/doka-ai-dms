import hashlib
import io

import pytest

from app.services.cloud_storage import (
    CloudinaryObjectStorage,
    QuotaGuard,
    R2ObjectStorage,
    StorageIntegrityError,
    StorageNotConfigured,
    normalize_key,
)


def test_normalize_key_rejects_traversal():
    for value in ("../secret", "/absolute", "a//b", "a/../b", "a/./b"):
        with pytest.raises(Exception):
            normalize_key(value)


def test_quota_enforces_exact_50_mib_boundary():
    quota = QuotaGuard(max_object_bytes=50 * 1024 * 1024)
    quota.check_object(50 * 1024 * 1024)
    with pytest.raises(Exception):
        quota.check_object(50 * 1024 * 1024 + 1)


def test_cloudinary_put_rejects_wrong_hash_before_network():
    provider = CloudinaryObjectStorage(
        cloud_name="test",
        api_key="test",
        api_secret="test",
    )
    with pytest.raises(StorageIntegrityError):
        provider.put(
            "acceptance/test.txt",
            io.BytesIO(b"fixture"),
            content_type="text/plain",
            expected_sha256=hashlib.sha256(b"other").hexdigest(),
        )


def test_r2_requires_complete_configuration():
    with pytest.raises(StorageNotConfigured):
        R2ObjectStorage(
            bucket="",
            endpoint_url="",
            access_key_id="",
            secret_access_key="",
        )
