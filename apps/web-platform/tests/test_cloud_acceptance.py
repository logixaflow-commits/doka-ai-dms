from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

_MODULE_SPEC = importlib.util.spec_from_file_location(
    "doka_cloud_acceptance",
    Path(__file__).resolve().parents[3] / "scripts" / "cloud_acceptance.py",
)
assert _MODULE_SPEC is not None and _MODULE_SPEC.loader is not None
DOKA_CLOUD_ACCEPTANCE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(DOKA_CLOUD_ACCEPTANCE)

_download_and_verify = DOKA_CLOUD_ACCEPTANCE._download_and_verify
_assert_cross_user_mutations_denied = DOKA_CLOUD_ACCEPTANCE._assert_cross_user_mutations_denied
_read_fifty_mib_fixture = DOKA_CLOUD_ACCEPTANCE._read_fifty_mib_fixture
_upload_document = DOKA_CLOUD_ACCEPTANCE._upload_document
_assert_staging_base_url = DOKA_CLOUD_ACCEPTANCE._assert_staging_base_url


def test_upload_uses_signed_provider_url_and_worker_completion():
    payload = b"signed direct upload acceptance"
    digest = hashlib.sha256(payload).hexdigest()
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host + request.url.path)
        if request.url.path == "/api/storage/upload-session":
            assert request.headers.get("authorization") == "Bearer user-token"
            body = json.loads(request.content)
            assert body["sha256"] == digest
            assert body["size_bytes"] == len(payload)
            return httpx.Response(
                200,
                json={
                    "session_id": "signed-session-token",
                    "provider": "supabase",
                    "upload": {
                        "method": "PUT",
                        "url": "https://storage.example/signed-upload",
                        "headers": {"content-type": "text/plain"},
                        "fields": {},
                    },
                },
            )
        if request.url.host == "storage.example":
            assert request.method == "PUT"
            assert request.content == payload
            assert "authorization" not in request.headers
            return httpx.Response(200)
        if request.url.path == "/api/storage/upload-complete":
            assert request.headers.get("authorization") == "Bearer user-token"
            body = json.loads(request.content)
            assert body["session_id"] == "signed-session-token"
            assert body["sha256"] == digest
            assert body["provider_result"] == {}
            return httpx.Response(
                200,
                json={
                    "document": {
                        "id": "document-123",
                        "sha256": digest,
                        "size_bytes": len(payload),
                        "storage_status": "ready",
                    },
                    "warnings": [],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client:
        document = _upload_document(client, "user-token", payload, "acceptance.txt", "text/plain")

    assert document["id"] == "document-123"
    assert document["_acceptance_provider"] == "supabase"
    assert seen == [
        "cloud.example/api/storage/upload-session",
        "storage.example/signed-upload",
        "cloud.example/api/storage/upload-complete",
    ]


def test_upload_rejects_provider_mismatch_before_upload():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host + request.url.path)
        assert request.url.path == "/api/storage/upload-session"
        return httpx.Response(
            200,
            json={
                "session_id": "session-1",
                "provider": "supabase",
                "upload": {
                    "method": "PUT",
                    "url": "https://storage.example/signed-upload",
                    "headers": {},
                },
            },
        )

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client, pytest.raises(AssertionError, match="expected 'b2'"):
        _upload_document(
            client,
            "user-token",
            b"provider mismatch",
            "acceptance.txt",
            "text/plain",
            expected_provider="b2",
        )

    # Fail before any provider upload or completion request is attempted.
    assert seen == ["cloud.example/api/storage/upload-session"]


def test_download_integrity_hashes_actual_downloaded_bytes():
    payload = b"actual object bytes"
    digest = hashlib.sha256(payload).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/documents/doc-1/download":
            assert request.headers.get("authorization") == "Bearer user-token"
            return httpx.Response(
                200,
                json={"url": "https://storage.example/signed-download", "sha256": digest},
            )
        if request.url.host == "storage.example":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=payload)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client:
        _download_and_verify(client, "user-token", "doc-1", digest)


def test_upload_rejects_non_https_signed_provider_url():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "session_id": "signed-session-token",
                "provider": "supabase",
                "upload": {"method": "PUT", "url": "http://storage.example/upload"},
            },
        )

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client, pytest.raises(AssertionError, match="safe HTTPS URL"):
        _upload_document(client, "user-token", b"x", "acceptance.txt", "text/plain")


def test_fifty_mib_fixture_rejects_symlinks(tmp_path):
    target = tmp_path / "target.bin"
    target.write_bytes(b"not a release fixture")
    link = tmp_path / "fixture.bin"
    try:
        link.symlink_to(target)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Symlink creation requires elevated privilege on Windows")
        raise

    with pytest.raises(AssertionError, match="non-symlink"):
        _read_fifty_mib_fixture(link)


def test_fifty_mib_fixture_requires_exact_size(tmp_path):
    fixture = tmp_path / "fixture.bin"
    fixture.write_bytes(b"too small")

    with pytest.raises(AssertionError, match="exactly 52428800 bytes"):
        _read_fifty_mib_fixture(fixture)


def test_cross_user_cannot_update_trash_or_permanently_delete_document():
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        assert request.headers.get("authorization") == "Bearer user-b-token"
        return httpx.Response(404, json={"detail": "not_found"})

    with httpx.Client(
        base_url="https://cloud.example", transport=httpx.MockTransport(handler)
    ) as client:
        _assert_cross_user_mutations_denied(client, "user-b-token", "owner-doc-123")

    assert seen == [
        ("PATCH", "/api/documents/owner-doc-123"),
        ("DELETE", "/api/documents/owner-doc-123"),
        ("DELETE", "/api/documents/owner-doc-123/permanent"),
    ]

def test_acceptance_runner_rejects_production_and_other_hosts():
    for url in (
        "https://doka-ai-dms.logixaflow.workers.dev",
        "https://enterprise-ai-dms.vercel.app",
        "https://doka-ai-dms-staging.example.workers.dev",
    ):
        with pytest.raises(SystemExit, match="exact dedicated staging Worker"):
            _assert_staging_base_url(url)


def test_acceptance_runner_allows_exact_staging_worker():
    _assert_staging_base_url("https://doka-ai-dms-staging.logixaflow.workers.dev")


def test_acceptance_runner_rejects_non_https_base_url():
    with pytest.raises(SystemExit, match="absolute HTTPS URL"):
        _assert_staging_base_url("http://doka-ai-dms-staging.logixaflow.workers.dev")



_PROVIDER_MODULE_SPEC = importlib.util.spec_from_file_location(
    "doka_cloud_provider_acceptance",
    Path(__file__).resolve().parents[3] / "scripts" / "cloud_provider_acceptance.py",
)
assert _PROVIDER_MODULE_SPEC is not None and _PROVIDER_MODULE_SPEC.loader is not None
DOKA_CLOUD_PROVIDER_ACCEPTANCE = importlib.util.module_from_spec(_PROVIDER_MODULE_SPEC)
_PROVIDER_MODULE_SPEC.loader.exec_module(DOKA_CLOUD_PROVIDER_ACCEPTANCE)


def test_provider_acceptance_runner_requires_staging_worker():
    with pytest.raises(SystemExit, match="exact dedicated staging Worker"):
        DOKA_CLOUD_PROVIDER_ACCEPTANCE.assert_staging_base_url(
            "https://doka-ai-dms.logixaflow.workers.dev"
        )
    DOKA_CLOUD_PROVIDER_ACCEPTANCE.assert_staging_base_url(
        "https://doka-ai-dms-staging.logixaflow.workers.dev"
    )



def test_provider_powershell_wrapper_defaults_to_staging():
    wrapper = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "run-cloud-provider-acceptance.ps1"
    ).read_text(encoding="utf-8")
    assert '[string]$BaseUrl = "https://doka-ai-dms-staging.logixaflow.workers.dev"' in wrapper
    assert '$parsed.Host -ne "doka-ai-dms-staging.logixaflow.workers.dev"' in wrapper
    assert '[string]$BaseUrl = "https://doka-ai-dms.logixaflow.workers.dev"' not in wrapper


def test_supabase_storage_boundary_probes_anonymous_and_cross_user_access():
    calls: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization")))
        return httpx.Response(403, json={"message": "row/object access denied"})

    DOKA_CLOUD_ACCEPTANCE._assert_supabase_storage_boundary(
        project_url="https://staging.supabase.example",
        publishable_key="public-test-key",
        other_token="user-b-token",
        object_key="users/user-a/documents/abc123/acceptance.txt",
        transport=httpx.MockTransport(handler),
    )

    assert [method for method, _, _ in calls] == ["POST", "GET", "POST", "GET", "DELETE"]
    assert calls[0][1].endswith("/storage/v1/object/list/doka-documents")
    assert calls[1][1].endswith("/storage/v1/object/authenticated/doka-documents/users/user-a/documents/abc123/acceptance.txt")
    assert calls[1][2] is None
    assert calls[2][1].endswith("/storage/v1/object/doka-documents/users/acceptance-anonymous-probe.txt")
    assert calls[3][2] == "Bearer user-b-token"
    assert calls[4][0] == "DELETE" and calls[4][2] == "Bearer user-b-token"


def test_supabase_storage_boundary_fails_if_anonymous_access_succeeds():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/object/list/doka-documents"):
            return httpx.Response(200, json=[])
        return httpx.Response(403, json={"message": "denied"})

    with pytest.raises(AssertionError, match="anonymous Storage list"):
        DOKA_CLOUD_ACCEPTANCE._assert_supabase_storage_boundary(
            project_url="https://staging.supabase.example",
            publishable_key="public-test-key",
            other_token="user-b-token",
            object_key="users/user-a/documents/abc123/acceptance.txt",
            transport=httpx.MockTransport(handler),
        )


def test_sensitive_rpc_probes_use_user_b_and_fail_closed_on_missing_rpc():
    import base64

    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "user-b-uuid"}).encode()
    ).decode().rstrip("=")
    token = "header." + payload + ".signature"
    seen: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == f"Bearer {token}"
        seen.append((request.url.path, json.loads(request.content)))
        return httpx.Response(404, json={"code": "P0002", "message": "Document not found"})

    DOKA_CLOUD_ACCEPTANCE._assert_rpc_owner_checks(
        project_url="https://staging.supabase.example",
        publishable_key="public-test-key",
        other_token=token,
        owner_document_id="owner-a-document-uuid",
        transport=httpx.MockTransport(handler),
    )

    assert len(seen) == 4
    assert {path.rsplit("/", 1)[-1] for path, _ in seen} == {
        "doka_bulk_update_documents",
        "doka_replace_document_version",
        "doka_replace_document_version_storage",
        "doka_restore_document_version",
    }
    assert all(
        "users/user-b-uuid/documents/" in str(payload)
        for path, payload in seen
        if path.endswith(("doka_replace_document_version", "doka_replace_document_version_storage"))
    )


def test_sensitive_rpc_probes_reject_missing_function_false_positive():
    import base64

    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "user-b-uuid"}).encode()
    ).decode().rstrip("=")
    token = "header." + payload + ".signature"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "PGRST202", "message": "function not found"})

    with pytest.raises(AssertionError, match="required RPC function is missing"):
        DOKA_CLOUD_ACCEPTANCE._assert_rpc_owner_checks(
            project_url="https://staging.supabase.example",
            publishable_key="public-test-key",
            other_token=token,
            owner_document_id="owner-a-document-uuid",
            transport=httpx.MockTransport(handler),
        )


def test_storage_denial_probe_does_not_treat_server_error_as_access_control():
    response = httpx.Response(500, json={"message": "internal error"})
    with pytest.raises(AssertionError, match="unexpected HTTP status 500"):
        DOKA_CLOUD_ACCEPTANCE._assert_denied(response, "anonymous Storage read")


def test_rpc_owner_probe_rejects_permission_error_as_false_positive():
    response = httpx.Response(403, json={"code": "42501", "message": "permission denied"})
    with pytest.raises(AssertionError, match="ownership/argument rejection"):
        DOKA_CLOUD_ACCEPTANCE._assert_rpc_denied(response, "cross-user RPC")
