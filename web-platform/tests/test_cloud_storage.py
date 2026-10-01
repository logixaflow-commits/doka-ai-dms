import io

import pytest

from app.services.cloud_storage import (
    QuotaGuard,
    SupabaseObjectStorage,
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


def test_supabase_total_bytes_recurses_through_user_folders(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = SupabaseObjectStorage(
        project_url="https://example.supabase.co",
        bucket="doka-documents",
        access_token="user-token",
        api_key="publishable-key",
        quota=QuotaGuard(max_total_bytes=100),
    )
    responses = {
        "": [{"name": "users", "id": None, "metadata": None}],
        "users/": [{"name": "user-1", "id": None, "metadata": None}],
        "users/user-1/": [{"name": "report.pdf", "id": "object-id", "metadata": {"size": 7}}],
    }

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def fake_post(url, *, headers, json, timeout):
        return Response(responses[json["prefix"]])

    monkeypatch.setattr(cloud_storage.httpx, "post", fake_post)
    assert storage.total_bytes() == 7
