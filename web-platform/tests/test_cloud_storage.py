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


def test_cloudinary_storage_builds_signed_private_upload(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.CloudinaryObjectStorage(
        cloud_name="demo",
        api_key="api-key",
        api_secret="api-secret",
        quota=QuotaGuard(max_object_bytes=100),
    )
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"public_id": "users/u1/report.pdf", "bytes": 4}

    def fake_post(url, *, data, files, timeout):
        calls.append((url, data, files, timeout))
        return Response()

    monkeypatch.setattr(cloud_storage.httpx, "post", fake_post)
    stored = storage.put(
        "users/u1/report.pdf",
        io.BytesIO(b"doka"),
        content_type="application/pdf",
        expected_sha256=__import__("hashlib").sha256(b"doka").hexdigest(),
    )

    assert stored.key == "users/u1/report.pdf"
    assert stored.size == 4
    assert stored.content_type == "application/pdf"
    assert calls[0][0] == "https://api.cloudinary.com/v1_1/demo/raw/upload"
    assert calls[0][1]["api_key"] == "api-key"
    assert calls[0][1]["type"] == "private"
    assert calls[0][1]["overwrite"] == "false"
    assert calls[0][1]["signature"]
    assert calls[0][2]["file"][1] == b"doka"


def test_cloudinary_signed_download_url_contains_expiry_and_signature(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.CloudinaryObjectStorage(
        cloud_name="demo",
        api_key="api-key",
        api_secret="api-secret",
    )
    url = storage.signed_get_url("users/u1/report.pdf", expires_seconds=900)

    assert url.startswith("https://api.cloudinary.com/v1_1/demo/raw/download?")
    assert "public_id=users%2Fu1%2Freport" in url
    assert "format=pdf" in url
    assert "expires_at=" in url
    assert "api_key=api-key" in url
    assert "signature=" in url


def test_cloudinary_storage_get_downloads_private_asset(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.CloudinaryObjectStorage(
        cloud_name="demo",
        api_key="api-key",
        api_secret="api-secret",
    )
    calls = []

    class Response:
        status_code = 200
        content = b"doka"

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if "/resources/raw/private/" in url:
            class MetadataResponse:
                status_code = 200

                def json(self):
                    return {"bytes": 4, "context": {"custom": {"sha256": __import__("hashlib").sha256(b"doka").hexdigest()}}}

            return MetadataResponse()
        return Response()

    monkeypatch.setattr(cloud_storage.httpx, "get", fake_get)
    assert storage.get("users/u1/report.pdf") == b"doka"
    assert calls[0][0].startswith("https://api.cloudinary.com/v1_1/demo/raw/download?")


def test_cloudinary_storage_head_uses_admin_api(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.CloudinaryObjectStorage(
        cloud_name="demo",
        api_key="api-key",
        api_secret="api-secret",
    )

    class Response:
        status_code = 200

        def json(self):
            return {"bytes": 7, "context": {}}

    monkeypatch.setattr(
        cloud_storage.httpx,
        "get",
        lambda url, *, auth, timeout: Response(),
    )
    result = storage.head("users/u1/report.pdf")
    assert result.size == 7
    assert result.content_type == "application/pdf"


def test_cloudinary_storage_delete_uses_signed_destroy(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.CloudinaryObjectStorage(
        cloud_name="demo",
        api_key="api-key",
        api_secret="api-secret",
    )
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"result": "ok"}

    def fake_post(url, *, data, timeout):
        calls.append((url, data, timeout))
        return Response()

    monkeypatch.setattr(cloud_storage.httpx, "post", fake_post)
    storage.delete("users/u1/report.pdf")
    assert calls[0][0] == "https://api.cloudinary.com/v1_1/demo/raw/destroy"
    assert calls[0][1]["type"] == "private"
    assert calls[0][1]["invalidate"] == "true"
    assert calls[0][1]["signature"]


def test_supabase_object_storage_rejects_oversized_source_before_network(monkeypatch):
    import app.services.cloud_storage as cloud_storage

    storage = cloud_storage.SupabaseObjectStorage(
        project_url="https://example.supabase.co",
        bucket="doka-documents",
        access_token="user-token",
        api_key="publishable-key",
        quota=QuotaGuard(max_object_bytes=4),
    )
    called = False

    def fake_post(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider must not be called for oversized input")

    monkeypatch.setattr(cloud_storage.httpx, "post", fake_post)
    with pytest.raises(StorageQuotaError):
        storage.put("users/u1/large.pdf", io.BytesIO(b"12345"), content_type="application/pdf")
    assert called is False
