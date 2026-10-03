"""HTTP-level characterization of current Cloud ASGI storage routes."""
from __future__ import annotations

import hashlib

import pytest
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api.routes import cloud_storage
from app.cloud_main import create_app
from app.core.local_security import bearer
from app.core.supabase_auth import require_authenticated_user
from app.services.cloud_storage import (
    StorageError,
    StorageNotConfigured,
    StoredObject,
)


TEST_USER_ID = "storage-characterization-user"
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


class FakeStorage:
    def __init__(
        self,
        *,
        put_error: Exception | None = None,
        get_error: Exception | None = None,
        head_error: Exception | None = None,
        signed_url_error: Exception | None = None,
    ):
        self.put_error = put_error
        self.get_error = get_error
        self.head_error = head_error
        self.signed_url_error = signed_url_error
        self.uploads = []
        self.downloads = []
        self.heads = []
        self.signed_urls = []

    def put(self, key, body, *, content_type, expected_sha256=None):
        data = body.read()
        self.uploads.append((key, data, content_type, expected_sha256))
        if self.put_error is not None:
            raise self.put_error
        return StoredObject(
            key=key,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    def get(self, key):
        self.downloads.append(key)
        if self.get_error is not None:
            raise self.get_error
        return b"fake object bytes"

    def head(self, key):
        self.heads.append(key)
        if self.head_error is not None:
            raise self.head_error
        return StoredObject(
            key=key,
            size=len(b"fake object bytes"),
            sha256=hashlib.sha256(b"fake object bytes").hexdigest(),
            content_type="application/octet-stream",
        )

    def signed_get_url(self, key, *, expires_seconds=900):
        self.signed_urls.append((key, expires_seconds))
        if self.signed_url_error is not None:
            raise self.signed_url_error
        return "https://signed.example.invalid/storage-object"


@pytest.fixture
def cloud_app(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://test.example.invalid")
    app = create_app()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(cloud_app):
    with TestClient(cloud_app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(cloud_app):
    async def authenticate(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ):
        if credentials is None or credentials.credentials != "test-token":
            raise HTTPException(status_code=401, detail="Authentication required.")
        return TEST_USER_ID

    cloud_app.dependency_overrides[require_authenticated_user] = authenticate
    with TestClient(cloud_app) as test_client:
        yield test_client


@pytest.fixture
def storage_factory(monkeypatch):
    storage = FakeStorage()
    calls = []

    def build_storage(**kwargs):
        calls.append(kwargs)
        return storage

    monkeypatch.setattr(cloud_storage, "build_object_storage", build_storage)
    return storage, calls


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        (
            "post",
            "/api/storage/objects?key=folder%2Fdocument.txt",
            {"files": {"file": ("document.txt", b"contents", "text/plain")}},
        ),
        ("get", "/api/storage/objects/folder/document.txt", {}),
        (
            "post",
            "/api/storage/signed-url",
            {"json": {"key": "folder/document.txt"}},
        ),
    ],
)
def test_storage_routes_reject_missing_authentication(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_storage_upload_uses_authenticated_user_namespace(
    authenticated_client, storage_factory
):
    storage, factory_calls = storage_factory
    content = b"characterization object"
    digest = hashlib.sha256(content).hexdigest()

    response = authenticated_client.post(
        "/api/storage/objects",
        params={"key": "reports/document.txt"},
        headers=AUTH_HEADERS,
        files={"file": ("document.txt", content, "text/plain")},
    )

    object_key = f"users/{TEST_USER_ID}/reports/document.txt"
    assert response.status_code == 200
    assert response.json() == {
        "key": "reports/document.txt",
        "size": len(content),
        "sha256": digest,
        "content_type": "text/plain",
    }
    assert factory_calls == [{"access_token": "test-token"}]
    assert storage.uploads == [
        (object_key, content, "text/plain", digest),
    ]


@pytest.mark.parametrize(
    ("path", "kwargs"),
    [
        (
            "/api/storage/objects",
            {"params": {"key": "reports/document.txt"}, "files": {}},
        ),
        (
            "/api/storage/objects",
            {"files": {"file": ("document.txt", b"x", "text/plain")}},
        ),
    ],
)
def test_storage_upload_requires_file_and_key(
    authenticated_client, monkeypatch, path, kwargs
):
    storage_factory_calls = []
    monkeypatch.setattr(
        cloud_storage,
        "build_object_storage",
        lambda **factory_kwargs: storage_factory_calls.append(factory_kwargs),
    )
    response = authenticated_client.post(path, headers=AUTH_HEADERS, **kwargs)

    assert response.status_code == 422
    assert storage_factory_calls == []


def test_storage_upload_over_limit_returns_current_413(
    authenticated_client, monkeypatch
):
    storage = FakeStorage()
    storage_factory_calls = []
    monkeypatch.setenv("DOKA_STORAGE_MAX_OBJECT_BYTES", "4")

    def build_storage(**kwargs):
        storage_factory_calls.append(kwargs)
        return storage

    monkeypatch.setattr(cloud_storage, "build_object_storage", build_storage)

    response = authenticated_client.post(
        "/api/storage/objects",
        params={"key": "reports/document.txt"},
        headers=AUTH_HEADERS,
        files={"file": ("document.txt", b"12345", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Object exceeds configured maximum size."
    assert storage_factory_calls == []
    assert storage.uploads == []


def test_storage_download_uses_authenticated_user_namespace(
    authenticated_client, storage_factory
):
    storage, factory_calls = storage_factory
    object_key = f"users/{TEST_USER_ID}/reports/document.txt"

    response = authenticated_client.get(
        "/api/storage/objects/reports/document.txt",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.content == b"fake object bytes"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == 'inline; filename="document.txt"'
    assert response.headers["x-doka-sha256"] == hashlib.sha256(
        b"fake object bytes"
    ).hexdigest()
    assert factory_calls == [{"access_token": "test-token"}]
    assert storage.downloads == [object_key]
    assert storage.heads == [object_key]


def test_signed_url_uses_authenticated_user_namespace_and_current_default_expiry(
    authenticated_client, storage_factory
):
    storage, factory_calls = storage_factory

    response = authenticated_client.post(
        "/api/storage/signed-url",
        headers=AUTH_HEADERS,
        json={"key": "reports/document.txt"},
    )

    object_key = f"users/{TEST_USER_ID}/reports/document.txt"
    assert response.status_code == 200
    assert response.json() == {
        "key": "reports/document.txt",
        "url": "https://signed.example.invalid/storage-object",
    }
    assert factory_calls == [{"access_token": "test-token"}]
    assert storage.signed_urls == [(object_key, 900)]


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({}, 422),
        ({"key": "reports/document.txt", "expires_seconds": 0}, 422),
        ({"key": "reports/document.txt", "expires_seconds": 604801}, 422),
    ],
)
def test_signed_url_rejects_missing_key_and_out_of_range_expiry(
    authenticated_client, storage_factory, payload, expected_status
):
    storage, factory_calls = storage_factory

    response = authenticated_client.post(
        "/api/storage/signed-url",
        headers=AUTH_HEADERS,
        json=payload,
    )

    assert response.status_code == expected_status
    assert factory_calls == []
    assert storage.signed_urls == []


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "error", "expected_status", "expected_detail"),
    [
        (
            "post",
            "/api/storage/objects",
            {
                "params": {"key": "reports/document.txt"},
                "files": {"file": ("document.txt", b"contents", "text/plain")},
            },
            StorageNotConfigured("storage provider is not configured"),
            503,
            "storage provider is not configured",
        ),
        (
            "post",
            "/api/storage/objects",
            {
                "params": {"key": "reports/document.txt"},
                "files": {"file": ("document.txt", b"contents", "text/plain")},
            },
            StorageError("storage upload failed (502)"),
            400,
            "storage upload failed (502)",
        ),
        (
            "get",
            "/api/storage/objects/reports/document.txt",
            {},
            StorageNotConfigured("storage provider is not configured"),
            503,
            "storage provider is not configured",
        ),
        (
            "get",
            "/api/storage/objects/reports/document.txt",
            {},
            StorageError("stored object was not found"),
            404,
            "stored object was not found",
        ),
        (
            "post",
            "/api/storage/signed-url",
            {"json": {"key": "reports/document.txt"}},
            StorageNotConfigured("storage provider is not configured"),
            503,
            "storage provider is not configured",
        ),
        (
            "post",
            "/api/storage/signed-url",
            {"json": {"key": "reports/document.txt"}},
            StorageError("signed URL provider failure"),
            400,
            "signed URL provider failure",
        ),
    ],
)
def test_storage_domain_errors_use_current_route_mapping(
    authenticated_client,
    monkeypatch,
    method,
    path,
    kwargs,
    error,
    expected_status,
    expected_detail,
):
    storage = FakeStorage(
        put_error=error if method == "post" and path.endswith("/objects") else None,
        get_error=error if method == "get" else None,
        signed_url_error=error if path.endswith("/signed-url") else None,
    )
    monkeypatch.setattr(
        cloud_storage,
        "build_object_storage",
        lambda **_kwargs: storage,
    )

    response = getattr(authenticated_client, method)(
        path,
        headers=AUTH_HEADERS,
        **kwargs,
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        (
            "post",
            "/api/storage/objects",
            {
                "params": {"key": "reports/document.txt"},
                "files": {"file": ("document.txt", b"contents", "text/plain")},
            },
        ),
        ("get", "/api/storage/objects/reports/document.txt", {}),
        (
            "post",
            "/api/storage/signed-url",
            {"json": {"key": "reports/document.txt"}},
        ),
    ],
)
def test_storage_initialization_failure_returns_current_503(
    authenticated_client, monkeypatch, method, path, kwargs
):
    factory_calls = []

    def fail_to_build_storage(**factory_kwargs):
        factory_calls.append(factory_kwargs)
        raise StorageNotConfigured("storage provider is not configured")

    monkeypatch.setattr(
        cloud_storage,
        "build_object_storage",
        fail_to_build_storage,
    )

    response = getattr(authenticated_client, method)(
        path,
        headers=AUTH_HEADERS,
        **kwargs,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "storage provider is not configured"
    assert len(factory_calls) == 1


def test_storage_head_error_uses_current_download_mapping(
    authenticated_client, monkeypatch
):
    storage = FakeStorage(head_error=StorageError("object metadata unavailable"))
    monkeypatch.setattr(
        cloud_storage,
        "build_object_storage",
        lambda **_kwargs: storage,
    )

    response = authenticated_client.get(
        "/api/storage/objects/reports/document.txt",
        headers=AUTH_HEADERS,
    )

    object_key = f"users/{TEST_USER_ID}/reports/document.txt"
    assert response.status_code == 404
    assert response.json()["detail"] == "object metadata unavailable"
    assert storage.downloads == [object_key]
    assert storage.heads == [object_key]


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_status", "factory_called"),
    [
        (
            "post",
            "/api/storage/objects",
            {
                "params": {"key": "../outside.txt"},
                "files": {"file": ("outside.txt", b"contents", "text/plain")},
            },
            400,
            False,
        ),
        (
            "get",
            "/api/storage/objects/reports/..%2Foutside.txt",
            {},
            404,
            True,
        ),
        (
            "post",
            "/api/storage/signed-url",
            {"json": {"key": "../outside.txt"}},
            400,
            True,
        ),
    ],
)
def test_storage_routes_map_unsafe_keys_using_current_behavior(
    authenticated_client,
    monkeypatch,
    method,
    path,
    kwargs,
    expected_status,
    factory_called,
):
    storage = FakeStorage()
    factory_calls = []

    def build_storage(**build_kwargs):
        factory_calls.append(build_kwargs)
        return storage

    monkeypatch.setattr(cloud_storage, "build_object_storage", build_storage)

    response = getattr(authenticated_client, method)(
        path,
        headers=AUTH_HEADERS,
        **kwargs,
    )

    assert response.status_code == expected_status
    assert bool(factory_calls) is factory_called
    assert storage.uploads == []
    assert storage.downloads == []
    assert storage.signed_urls == []
