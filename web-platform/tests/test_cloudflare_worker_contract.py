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

VERSION_RPC_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20261002101000_doka_version_rpc_final_hardening.sql"
).read_text(encoding="utf-8")


def test_version_rpc_privilege_boundary_and_input_guards_are_explicit():
    assert "security definer" in VERSION_RPC_MIGRATION.lower()
    assert "set search_path = pg_catalog, public, pg_temp" in VERSION_RPC_MIGRATION
    assert VERSION_RPC_MIGRATION.count("if auth.uid() is null") == 2
    assert "p_object_key is null" in VERSION_RPC_MIGRATION
    assert "chosen.object_key is null" in VERSION_RPC_MIGRATION
    assert "p_object_key not like 'users/' || auth.uid()::text || '/documents/' || p_sha256 || '/%'" in VERSION_RPC_MIGRATION
    assert "chosen.object_key not like 'users/' || auth.uid()::text || '/documents/' || chosen.sha256 || '/%'" in VERSION_RPC_MIGRATION
    assert "position('/' in p_filename) > 0" in VERSION_RPC_MIGRATION
    assert "position('/' in p_content_type) = 0" in VERSION_RPC_MIGRATION
    assert VERSION_RPC_MIGRATION.count("owner_id = auth.uid()") >= 2
    assert "from public, anon" in VERSION_RPC_MIGRATION
    assert "to authenticated" in VERSION_RPC_MIGRATION


def test_version_rpc_does_not_grant_direct_storage_pointer_updates():
    least_privilege = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "20261001100118_doka_least_privilege_grants.sql"
    ).read_text(encoding="utf-8")
    assert "grant update (status, metadata) on table public.doka_documents to authenticated" in least_privilege
    assert "grant update (object_key" not in least_privilege.lower()


def test_worker_version_upload_reuses_existing_objects_without_deleting_them_on_failure():
    assert 'version_query = f"select=id&document_id=eq.' in WORKER_SOURCE
    assert 'uploaded_new_object = False' in WORKER_SOURCE
    assert 'uploaded_new_object = True' in WORKER_SOURCE
    assert 'if uploaded_new_object:' in WORKER_SOURCE


def test_worker_version_upload_validates_filename_and_content_type():
    assert 'Filename must be a plain file name up to 255 characters.' in WORKER_SOURCE
    assert 'content_type = (file.content_type or "application/octet-stream")' in WORKER_SOURCE
    assert 'len(filename) > 255' in WORKER_SOURCE
    assert 'len(content_type) > 255' in WORKER_SOURCE
