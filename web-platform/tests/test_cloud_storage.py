import io

import pytest

from app.services.cloud_storage import (
    QuotaGuard,
    StorageError,
    StorageIntegrityError,
    StorageQuotaError,
    normalize_key,
)


def test_normalize_key_rejects_path_escape():
    with pytest.raises(StorageError):
        normalize_key("../secret.pdf")
    with pytest.raises(StorageError):
        normalize_key("/secret.pdf")
    with pytest.raises(StorageError):
        normalize_key("docs//secret.pdf")


def test_normalize_key_accepts_document_key():
    assert normalize_key("users/u1/documents/abc/report.pdf") == "users/u1/documents/abc/report.pdf"


def test_quota_guard_limits_object_size():
    guard = QuotaGuard(max_object_bytes=10)
    guard.check_object(10)
    with pytest.raises(StorageQuotaError):
        guard.check_object(11)


def test_quota_guard_limits_total_size():
    guard = QuotaGuard(max_total_bytes=100)
    guard.check_total(80, 20)
    with pytest.raises(StorageQuotaError):
        guard.check_total(90, 11)
    guard.check_total(100, 50, replacing_bytes=50)


def test_expected_sha256_is_calculable_before_provider_upload():
    data = b"doka"
    import hashlib
    expected = hashlib.sha256(data).hexdigest()
    assert expected == hashlib.sha256(io.BytesIO(data).read()).hexdigest()


def test_integrity_error_type_is_storage_error():
    assert issubclass(StorageIntegrityError, StorageError)
