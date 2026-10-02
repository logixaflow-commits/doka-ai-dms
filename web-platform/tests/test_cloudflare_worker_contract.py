"""Regression guard for the Cloudflare Worker safe-preview contract."""
from pathlib import Path


WORKER_SOURCE = (
    Path(__file__).resolve().parents[2] / "cloudflare_worker" / "main.py"
).read_text(encoding="utf-8")


def test_worker_preview_route_is_authenticated_and_owner_scoped():
    assert '@app.get("/api/documents/{document_id}/preview")' in WORKER_SOURCE
    assert 'user_id: str = Depends(require_user)' in WORKER_SOURCE
    assert '&owner_id=eq.{quote(user_id, safe=\'\')}&deleted_at=is.null&limit=1' in WORKER_SOURCE


def test_worker_preview_allows_only_passive_formats_and_audits():
    for content_type in (
        '"application/pdf"',
        '"image/jpeg"',
        '"image/png"',
        '"image/gif"',
        '"image/webp"',
        '"text/plain"',
        '"text/csv"',
    ):
        assert content_type in WORKER_SOURCE
    assert 'status_code=415, detail="Preview is not available for this file type."' in WORKER_SOURCE
    assert '_audit(request, user_id, "preview"' in WORKER_SOURCE


def test_worker_version_history_is_owner_scoped_and_uses_atomic_database_functions():
    assert '@app.get("/api/documents/{document_id}/versions")' in WORKER_SOURCE
    assert '@app.post("/api/documents/{document_id}/versions")' in WORKER_SOURCE
    assert '@app.post("/api/documents/{document_id}/versions/{version_id}/restore")' in WORKER_SOURCE
    assert 'rpc/doka_replace_document_version' in WORKER_SOURCE
    assert 'rpc/doka_restore_document_version' in WORKER_SOURCE
    assert '_audit(request, user_id, "version_create"' in WORKER_SOURCE
    assert '_audit(request, user_id, "version_restore"' in WORKER_SOURCE


def test_worker_bulk_actions_use_single_atomic_owner_scoped_rpc():
    assert '@app.post("/api/documents/bulk")' in WORKER_SOURCE
    assert 'rpc/doka_bulk_update_documents' in WORKER_SOURCE
    assert 'Duplicate document IDs are not allowed.' in WORKER_SOURCE
    assert 'action: Literal["status", "trash"]' in WORKER_SOURCE


def test_worker_folder_listing_is_owner_scoped():
    assert '@app.get("/api/folders")' in WORKER_SOURCE
    assert 'deleted_at=is.null&order=folder_path.asc&limit=500' in WORKER_SOURCE


def test_worker_version_events_use_distinct_audit_actions():
    assert '_audit(request, user_id, "version_create"' in WORKER_SOURCE
    assert '_audit(request, user_id, "version_restore"' in WORKER_SOURCE
