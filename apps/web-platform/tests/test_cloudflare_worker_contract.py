"""Regression guard for the Cloudflare Worker safe-preview contract."""
from pathlib import Path
import re


WORKER_SOURCE = (
    Path(__file__).resolve().parents[1] / "backend" / "cloudflare_worker" / "main.py"
).read_text(encoding="utf-8")


def test_worker_preview_route_is_authenticated_and_owner_scoped():
    assert '@app.get("/api/documents/{document_id}/preview")' in WORKER_SOURCE
    assert 'user_id: str = Depends(require_user)' in WORKER_SOURCE
    assert '&owner_id=eq.{quote(user_id, safe=\'\')}&deleted_at=is.null&storage_status=eq.ready&limit=1' in WORKER_SOURCE


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
    assert 'rpc/doka_replace_document_version_storage' in WORKER_SOURCE
    assert 'rpc/doka_restore_document_version' in WORKER_SOURCE
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
    Path(__file__).resolve().parents[1]
    / "backend"
    / "supabase"
    / "migrations"
    / "20261002100658_doka_version_object_key_pattern.sql"
).read_text(encoding="utf-8")


def test_version_rpc_privilege_boundary_and_input_guards_are_explicit():
    assert "security definer" in VERSION_RPC_MIGRATION.lower()
    assert "set search_path = pg_catalog, public, pg_temp" in VERSION_RPC_MIGRATION
    assert VERSION_RPC_MIGRATION.count("if auth.uid() is null") == 2
    assert "p_object_key is null" in VERSION_RPC_MIGRATION
    assert "chosen.object_key is null" in VERSION_RPC_MIGRATION
    assert "p_object_key !~" in VERSION_RPC_MIGRATION
    assert "chosen.object_key !~" in VERSION_RPC_MIGRATION
    assert "A-Za-z0-9._-" in VERSION_RPC_MIGRATION
    assert "{0,254}$" in VERSION_RPC_MIGRATION
    assert "position('/' in p_filename) > 0" in VERSION_RPC_MIGRATION
    assert "position('/' in p_content_type) = 0" in VERSION_RPC_MIGRATION
    assert "length(p_filename) > 255" in VERSION_RPC_MIGRATION
    assert "length(p_content_type) > 255" in VERSION_RPC_MIGRATION
    assert VERSION_RPC_MIGRATION.count("owner_id = auth.uid()") >= 2
    assert "from public, anon" in VERSION_RPC_MIGRATION
    assert "to authenticated" in VERSION_RPC_MIGRATION


def test_version_rpc_does_not_grant_direct_storage_pointer_updates():
    least_privilege = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "supabase"
        / "migrations"
        / "20261001100118_doka_least_privilege_grants.sql"
    ).read_text(encoding="utf-8")
    assert "grant update (status, metadata) on table public.doka_documents to authenticated" in least_privilege
    assert "grant update (object_key" not in least_privilege.lower()


def test_worker_version_upload_is_direct_only_and_legacy_proxy_is_disabled():
    assert 'Direct version upload is required. Create a storage upload session with document_id first.' in WORKER_SOURCE
    assert 'await file.read()' not in WORKER_SOURCE


def test_worker_version_upload_validates_filename_and_content_type_via_shared_metadata_guard():
    assert 'Filename must be a plain file name up to 255 characters.' in WORKER_SOURCE
    assert 'Invalid content type.' in WORKER_SOURCE
    assert 'len(filename) > 255' in WORKER_SOURCE
    assert 'len(content_type) > 255' in WORKER_SOURCE


def test_worker_route_method_and_path_pairs_are_unique():
    route_pairs = re.findall(
        r'@app\.(get|post|patch|delete|put)\("([^"]+)"',
        WORKER_SOURCE,
    )
    assert len(route_pairs) == len(set(route_pairs))


AUDIT_ACL_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "supabase"
    / "migrations"
    / "20261002114801_doka_audit_least_privilege.sql"
).read_text(encoding="utf-8")


def test_audit_table_is_append_only_for_authenticated_users():
    assert "revoke all privileges on table public.doka_audit_events from public, anon, authenticated" in AUDIT_ACL_MIGRATION
    assert "grant select, insert on table public.doka_audit_events to authenticated" in AUDIT_ACL_MIGRATION


VERSION_HISTORY_ACL_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "supabase"
    / "migrations"
    / "20261002115107_doka_version_history_append_only.sql"
).read_text(encoding="utf-8")


def test_version_history_cannot_be_deleted_directly_by_authenticated_users():
    assert "revoke delete on table public.doka_document_versions from authenticated" in VERSION_HISTORY_ACL_MIGRATION
    assert "drop policy if exists doka_versions_owner_delete" in VERSION_HISTORY_ACL_MIGRATION


def test_worker_legacy_document_upload_is_disabled_and_session_metadata_is_validated():
    assert '@app.post("/api/documents")' in WORKER_SOURCE
    legacy_route = WORKER_SOURCE.split('@app.post("/api/documents")', 1)[1].split('class UploadSessionRequest', 1)[0]
    assert 'status_code=410' in legacy_route
    assert 'Direct upload is required. Create an upload session first.' in legacy_route
    metadata_guard = WORKER_SOURCE.split('def _validate_upload_metadata', 1)[1].split('async def _check_b2_quota', 1)[0]
    assert 'Filename must be a plain file name up to 255 characters.' in metadata_guard
    assert 'Invalid content type.' in metadata_guard
    assert 'any(ord(character) < 32 or ord(character) == 127 for character in filename)' in metadata_guard
    assert 'len(content_type) > 255 or "/" not in content_type' in metadata_guard
    assert 'UploadMetadata(filename, content_type, size_bytes, sha256, user_id, artifact_type)' in metadata_guard



def test_worker_supports_optional_single_user_allowlist_without_disabling_auth():
    assert 'DOKA_SINGLE_USER_EMAIL' in WORKER_SOURCE
    assert 'status_code=403' in WORKER_SOURCE
    assert 'This Doka instance is restricted to its configured single user.' in WORKER_SOURCE
    assert 'Depends(require_user)' in WORKER_SOURCE

def test_worker_config_exposes_single_user_readiness_without_exposing_identity():
    assert '"single_user_configured": bool(_env(request, "DOKA_SINGLE_USER_EMAIL").strip())' in WORKER_SOURCE



WRANGLER = (Path(__file__).resolve().parents[3] / "wrangler.jsonc").read_text(encoding="utf-8")

def test_worker_rate_limit_binding_is_declared_and_user_scoped():
    assert '"ratelimits"' in WRANGLER
    assert '"name": "DOKA_RATE_LIMITER"' in WRANGLER
    assert '"namespace_id": "7101001"' in WRANGLER
    assert '"limit": 100' in WRANGLER
    assert '"period": 60' in WRANGLER
    assert 'DOKA_RATE_LIMITER' in WORKER_SOURCE
    assert 'limiter.limit({"key": str(user["id"])})' in WORKER_SOURCE


def test_worker_permanent_delete_is_provider_aware_and_retains_metadata_on_cleanup_failure():
    assert 'select=id,object_key,filename,storage_provider' in WORKER_SOURCE
    assert 'select=object_key,storage_provider' in WORKER_SOURCE
    assert 'build_storage_router(request, token, _storage_fetcher)' in WORKER_SOURCE
    assert 'provider.delete(StorageObjectRef(provider_name, object_key, user_id))' in WORKER_SOURCE
    assert 'Stored file cleanup failed; document metadata was retained.' in WORKER_SOURCE
    assert 'deleted_version_objects": len(objects) - 1' in WORKER_SOURCE


def test_worker_telegram_status_reports_topic_and_secret_readiness_without_exposing_values():
    status_block = WORKER_SOURCE.split('elif command == "/status":', 1)[1].split(
        'elif command in {"/morning_brief", "/digest"}:', 1
    )[0]
    assert '"TELEGRAM_BOT_TOKEN"' in status_block
    assert '"TELEGRAM_CHAT_ID"' in status_block
    assert "TELEGRAM_ALLOWED_CHAT_ID = \"-1003992125718\"" in WORKER_SOURCE
    assert "TELEGRAM_ALLOWED_TOPIC_ID = 8" in WORKER_SOURCE
    assert '"TELEGRAM_TOPIC_ID": "8"' in WRANGLER
    assert "TELEGRAM_TOPIC_ID" not in status_block
    assert '"TELEGRAM_WEBHOOK_SECRET"' in status_block
    assert "Telegram target topic" in status_block
    assert "Telegram outbound" in status_block
    assert "Telegram inbound webhook" in status_block
    assert "message_thread_id" not in status_block
    assert "token}" not in status_block


def test_worker_telegram_diagnostic_is_secret_gated_and_never_returns_token():
    route = WORKER_SOURCE.split('@app.post("/api/telegram/diagnostic")', 1)[1].split(
        'Default = asgi.entrypoint(app)', 1
    )[0]
    assert 'X-Doka-Diagnostic-Secret' in route
    assert 'hmac.compare_digest' in route
    assert 'TELEGRAM_WEBHOOK_SECRET' in route
    assert 'api.telegram.org/bot{token}/getMe' in route
    assert '"telegram_http_status": status' in route
    assert '"bot_username"' in route
    assert '"description"' in route
    assert 'return {"token": token}' not in route
    assert 'logger.warning("Telegram token diagnostic request failed.")' in route



def test_worker_telegram_webhook_registration_is_fixed_destination_and_verifies_remote_state():
    route = WORKER_SOURCE.split('@app.post("/api/telegram/webhook/register")', 1)[1].split(
        "\n\nDefault = asgi.entrypoint(app)", 1
    )[0]
    assert "TELEGRAM_WEBHOOK_ADMIN_SECRET" in route
    assert "X-Doka-Telegram-Admin" in route
    assert "hmac.compare_digest" in route
    assert 'webhook_url = "https://doka-ai-dms.logixaflow.workers.dev/api/telegram/webhook"' in route
    assert 'request.json' not in route
    assert 'api.telegram.org/bot{token}/setWebhook' in route
    assert 'api.telegram.org/bot{token}/getWebhookInfo' in route
    assert 'api.telegram.org/bot{token}/getMe' in route
    assert '"secret_token": webhook_secret' in route
    assert '"drop_pending_updates": False' in route
    assert '"webhook_url_matches": bool(url_matches)' in route
    assert '"bot_username": me.get("username") if identity_ok else None' in route


def test_telegram_api_responses_are_parsed_from_text_for_pyodide_compatibility():
    helper = WORKER_SOURCE.split("async def _telegram_response_payload", 1)[1].split(
        "async def _telegram_bot_identity", 1
    )[0]
    assert "await response.text()" in helper
    assert "json.loads(raw)" in helper
    assert "return payload if isinstance(payload, dict) else {}" in helper
    registration = WORKER_SOURCE.split('@app.post("/api/telegram/webhook/register")', 1)[1].split(
        "\n\nDefault = asgi.entrypoint(app)", 1
    )[0]
    assert "await _telegram_response_payload(set_response)" in registration
    assert "await _telegram_response_payload(info_response)" in registration
    assert "await _telegram_response_payload(me_response)" in registration
    assert '"bot_api_description": me_payload.get("description") if not identity_ok else None' in registration


SECURITY_INTEGRITY_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "supabase"
    / "migrations"
    / "20261110090000_doka_security_integrity_remediation.sql"
).read_text(encoding="utf-8")


def test_audit_and_version_direct_insert_are_revoked_and_audit_rpc_is_owner_scoped():
    source = SECURITY_INTEGRITY_MIGRATION.lower()
    assert "revoke insert on table public.doka_audit_events from authenticated" in source
    assert "revoke insert on table public.doka_document_versions from authenticated" in source
    assert "drop policy if exists doka_audit_owner_insert" in source
    assert "revoke all on function public.doka_record_audit_event" in source
    assert "from public, anon, authenticated, service_role" in source
    assert "grant execute on function public.doka_record_audit_event" in source
    assert "to authenticated" in source
    assert "p_owner_id is distinct from auth.uid()" in source


def test_version_rpcs_keep_atomic_database_boundary_and_direct_insert_is_removed():
    source = SECURITY_INTEGRITY_MIGRATION.lower()
    assert "revoke insert on table public.doka_document_versions from authenticated" in source
    assert "grant execute on function public.doka_replace_document_version" in source
    assert "grant execute on function public.doka_replace_document_version_storage" in source
    assert "grant execute on function public.doka_restore_document_version" in source


def test_worker_audit_fails_closed_uses_owner_jwt_rpc_and_retries_with_structured_logs():
    audit_block = WORKER_SOURCE.split("async def _audit", 1)[1].split('@app.post("/api/documents")', 1)[0]
    assert "rest/v1/rpc/doka_record_audit_event" in WORKER_SOURCE
    assert '_token_from_request(request)' in audit_block
    assert 'headers=_supabase_headers(request, token, "application/json")' in audit_block
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in WORKER_SOURCE
    assert "AUDIT_MAX_ATTEMPTS = 3" in WORKER_SOURCE
    assert '"audit_write_retry"' in WORKER_SOURCE
    assert '"audit_write_failed"' in WORKER_SOURCE
    assert "except Exception:\\n        pass" not in audit_block
    assert 'status_code=503' in audit_block

def test_b2_multipart_api_is_owner_scoped_and_requires_both_part_hashes_and_abort():
    assert '@app.post("/api/storage/multipart/initiate")' in WORKER_SOURCE
    assert '@app.post("/api/storage/multipart/part")' in WORKER_SOURCE
    assert '@app.post("/api/storage/multipart/complete")' in WORKER_SOURCE
    assert '@app.post("/api/storage/multipart/abort")' in WORKER_SOURCE
    assert 'content_md5: str = Field(min_length=32, max_length=32)' in WORKER_SOURCE
    assert 'await _check_b2_quota(request, user_id, metadata.size_bytes)' in WORKER_SOURCE
    assert 'checksum: str = Field(min_length=64, max_length=64)' in WORKER_SOURCE
    assert 'receipt = await router.b2.uploadPart(upload, payload.part_number, payload.checksum, payload.content_md5)' in WORKER_SOURCE
    assert 'Multipart session is not valid for this user.' in WORKER_SOURCE
    assert 'expected_size_bytes=int(signed["size_bytes"])' in WORKER_SOURCE
    assert 'expected_sha256=str(signed["sha256"]).lower()' in WORKER_SOURCE


def test_worker_telegram_commands_require_an_allowlisted_sender_id():
    assert 'TELEGRAM_ALLOWED_USER_IDS = frozenset({"1686310706", "6759217947"})' in WORKER_SOURCE
    assert 'def _telegram_sender_allowed(sender_id) -> bool:' in WORKER_SOURCE
    assert 'sender_id is None or isinstance(sender_id, bool)' in WORKER_SOURCE
    assert 'if not _telegram_sender_allowed(sender_id):' in WORKER_SOURCE
    assert '"reason": "unauthorized_sender"' in WORKER_SOURCE

def test_forward_migration_uses_owner_checked_definer_rpcs_and_sha_bound_keys():
    source = SECURITY_INTEGRITY_MIGRATION.lower()
    assert source.count("security definer") >= 5
    assert source.count("set search_path = pg_catalog, public, pg_temp") >= 5
    assert source.count("auth.uid()") >= 10
    assert "p_owner_id is distinct from auth.uid()" in source
    assert "p_object_key !~ ('^users/' || auth.uid()::text || '/documents/' || p_sha256" in source
    assert "chosen.object_key !~ ('^users/' || auth.uid()::text || '/documents/' || chosen.sha256" in source
    assert "to service_role" not in source
