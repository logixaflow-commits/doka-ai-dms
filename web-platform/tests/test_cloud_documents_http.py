"""HTTP-level characterization of current Cloud ASGI document behavior.

These tests document the ASGI implementation only; they do not define the
approved API contract or assert parity with the Cloudflare Worker.
"""
from __future__ import annotations

import hashlib

import pytest
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from app.api.routes import cloud_documents
from app.cloud_main import create_app
from app.core.local_security import bearer
from app.core.supabase_auth import require_authenticated_user
from app.services.cloud_documents import CloudDocumentError
from app.services.cloud_storage import StoredObject


TEST_USER_ID = "characterization-user"
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


class FakeDocumentService:
    def __init__(self, events: list[tuple], *, document=None, create_error=None):
        self.events = events
        self.document = document
        self.create_error = create_error
        self.listed = []
        self.lookups = []
        self.created = []
        self.base_url = "https://supabase.invalid"

    def list_documents(self, *, limit, offset):
        self.events.append(("list", limit, offset))
        self.listed.append((limit, offset))
        return [{"id": "doc-1"}]

    def get_document(self, *, owner_id, document_id):
        self.events.append(("get", owner_id, document_id))
        self.lookups.append((owner_id, document_id))
        return self.document

    def create_document(self, **fields):
        self.events.append(("create", fields))
        self.created.append(fields)
        if self.create_error is not None:
            raise self.create_error
        return {"id": "doc-1", **fields}

    def _headers(self):
        return {"Authorization": "Bearer test-token"}


class FakeObjectStorage:
    def __init__(self, events: list[tuple]):
        self.events = events
        self.uploads = []
        self.deletions = []
        self.signed_urls = []

    def put(self, key, body, *, content_type, expected_sha256=None):
        data = body.read()
        self.events.append(("put", key))
        self.uploads.append((key, data, content_type, expected_sha256))
        return StoredObject(
            key=key,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    def delete(self, key):
        self.events.append(("delete", key))
        self.deletions.append(key)

    def signed_get_url(self, key, *, expires_seconds=900):
        self.events.append(("signed_get_url", key, expires_seconds))
        self.signed_urls.append((key, expires_seconds))
        return "https://signed.example.invalid/object"


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
def fakes(monkeypatch):
    events: list[tuple] = []
    service = FakeDocumentService(
        events,
        document={
            "id": "doc-1",
            "object_key": "users/characterization-user/documents/hash/report.pdf",
            "sha256": "a" * 64,
        },
    )
    storage = FakeObjectStorage(events)
    monkeypatch.setattr(
        cloud_documents,
        "build_cloud_document_service",
        lambda _access_token: service,
    )
    monkeypatch.setattr(
        cloud_documents,
        "build_object_storage",
        lambda **_kwargs: storage,
    )
    return service, storage, events


def test_missing_authentication_returns_current_401(client):
    response = client.get("/api/documents")

    assert response.status_code == 401


def test_document_listing_returns_documents_and_forwards_pagination(
    authenticated_client, fakes
):
    service, _, _ = fakes

    response = authenticated_client.get(
        "/api/documents?limit=23&offset=7",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"documents": [{"id": "doc-1"}]}
    assert service.listed == [(23, 7)]


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("limit=0", "Invalid limit/offset."),
        ("limit=501", "Invalid limit/offset."),
        ("offset=-1", "Invalid limit/offset."),
    ],
)
def test_invalid_document_pagination_returns_current_400(
    authenticated_client, fakes, query, detail
):
    service, _, _ = fakes

    response = authenticated_client.get(
        f"/api/documents?{query}",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == detail
    assert service.listed == []


def test_multipart_upload_stores_object_before_creating_metadata(
    authenticated_client, fakes
):
    service, storage, events = fakes
    content = b"characterization upload"
    digest = hashlib.sha256(content).hexdigest()

    response = authenticated_client.post(
        "/api/documents",
        headers=AUTH_HEADERS,
        files={"file": ("quarterly report.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    document = response.json()["document"]
    assert document["id"] == "doc-1"
    assert storage.uploads == [
        (
            f"users/{TEST_USER_ID}/documents/{digest}/quarterly_report.pdf",
            content,
            "application/pdf",
            digest,
        )
    ]
    assert service.created == [
        {
            "owner_id": TEST_USER_ID,
            "object_key": f"users/{TEST_USER_ID}/documents/{digest}/quarterly_report.pdf",
            "filename": "quarterly report.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(content),
            "sha256": digest,
        }
    ]
    assert events == [
        ("put", storage.uploads[0][0]),
        ("create", service.created[0]),
    ]


def test_oversized_upload_returns_current_413_without_storage_calls(
    authenticated_client, fakes, monkeypatch
):
    _, storage, _ = fakes
    monkeypatch.setenv("DOKA_STORAGE_MAX_OBJECT_BYTES", "4")

    response = authenticated_client.post(
        "/api/documents",
        headers=AUTH_HEADERS,
        files={"file": ("small.txt", b"12345", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Object exceeds configured maximum size."
    assert storage.uploads == []


def test_metadata_creation_failure_returns_503_and_attempts_object_cleanup(
    authenticated_client, fakes
):
    service, storage, events = fakes
    service.create_error = CloudDocumentError("metadata creation failed")

    response = authenticated_client.post(
        "/api/documents",
        headers=AUTH_HEADERS,
        files={"file": ("report.txt", b"contents", "text/plain")},
    )

    uploaded_key = storage.uploads[0][0]
    assert response.status_code == 503
    assert response.json()["detail"] == "metadata creation failed"
    assert events[-1] == ("delete", uploaded_key)
    assert storage.deletions == [uploaded_key]


def test_download_returns_signed_url_and_requests_300_second_expiry(
    authenticated_client, fakes
):
    _, storage, _ = fakes

    response = authenticated_client.get(
        "/api/documents/doc-1/download",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "url": "https://signed.example.invalid/object",
        "sha256": "a" * 64,
        "expires_seconds": 300,
    }
    assert storage.signed_urls == [
        ("users/characterization-user/documents/hash/report.pdf", 300)
    ]


def test_missing_download_document_returns_404_without_storage_call(
    authenticated_client, fakes, monkeypatch
):
    service, storage, _ = fakes
    service.document = None
    storage_factory_calls = []
    monkeypatch.setattr(
        cloud_documents,
        "build_object_storage",
        lambda **kwargs: storage_factory_calls.append(kwargs),
    )

    response = authenticated_client.get(
        "/api/documents/missing/download",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."
    assert storage_factory_calls == []
    assert storage.signed_urls == []


def test_patch_sends_only_non_null_supported_fields_and_owner_document_params(
    authenticated_client, fakes, monkeypatch
):
    service, _, _ = fakes
    upstream_calls = []
    updated_document = {"id": "doc-1", "status": "review"}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return [updated_document]

    def fake_patch(url, *, headers, params, json, timeout):
        upstream_calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(cloud_documents.httpx, "patch", fake_patch)

    response = authenticated_client.patch(
        "/api/documents/doc-1",
        headers=AUTH_HEADERS,
        json={"status": "review", "metadata": None},
    )

    assert response.status_code == 200
    assert response.json() == {"document": updated_document}
    assert service.lookups == [(TEST_USER_ID, "doc-1")]
    assert len(upstream_calls) == 1
    assert upstream_calls[0]["params"] == {
        "id": "eq.doc-1",
        "owner_id": f"eq.{TEST_USER_ID}",
    }
    assert upstream_calls[0]["json"] == {"status": "review"}
    assert upstream_calls[0]["url"] == (
        "https://supabase.invalid/rest/v1/doka_documents"
    )


def test_missing_patch_document_returns_404_without_upstream_patch(
    authenticated_client, fakes, monkeypatch
):
    service, _, _ = fakes
    service.document = None
    upstream_calls = []
    monkeypatch.setattr(
        cloud_documents.httpx,
        "patch",
        lambda *args, **kwargs: upstream_calls.append((args, kwargs)),
    )

    response = authenticated_client.patch(
        "/api/documents/missing",
        headers=AUTH_HEADERS,
        json={"status": "review"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."
    assert upstream_calls == []


def test_invalid_patch_schema_is_rejected_before_service_call(
    authenticated_client, fakes, monkeypatch
):
    service, _, _ = fakes
    service_factory_calls = []
    monkeypatch.setattr(
        cloud_documents,
        "build_cloud_document_service",
        lambda access_token: service_factory_calls.append(access_token),
    )

    response = authenticated_client.patch(
        "/api/documents/doc-1",
        headers=AUTH_HEADERS,
        json={"status": "not-a-supported-status"},
    )

    assert response.status_code == 422
    assert service_factory_calls == []
    assert service.lookups == []
