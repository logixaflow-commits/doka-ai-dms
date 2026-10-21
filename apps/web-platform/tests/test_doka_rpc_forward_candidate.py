from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_PATH = (
    REPO_ROOT / "apps" / "web-platform" / "backend" / "supabase" / "candidates"
    / "20261021_doka_rpc_forward_hardening.sql"
)
CANDIDATE = CANDIDATE_PATH.read_text(encoding="utf-8").lower()


def function_definition(name: str) -> str:
    match = re.search(
        rf"create or replace function public\.{re.escape(name)}\(.*?\$function\$;",
        CANDIDATE,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"missing candidate definition for {name}"
    return match.group(0)


def test_candidate_is_not_in_the_supabase_migration_autorun_directory():
    assert "candidates" in CANDIDATE_PATH.parts
    assert "migrations" not in CANDIDATE_PATH.parts
    assert "do not move into supabase/migrations or apply until issue #82" in CANDIDATE


def test_bulk_status_trash_remains_invoker_and_owner_scoped():
    definition = function_definition("doka_bulk_update_documents")
    assert "security invoker" in definition
    assert "set search_path = pg_catalog, public, pg_temp" in definition
    assert "auth.uid()" in definition
    assert "owner_id = v_user" in definition
    assert "cardinality(p_document_ids) > 100" in definition
    assert "p_action not in ('status', 'trash')" in definition


def test_protected_version_pointer_rpcs_are_definer_with_owner_checks():
    for name in (
        "doka_replace_document_version",
        "doka_replace_document_version_storage",
        "doka_restore_document_version",
    ):
        definition = function_definition(name)
        assert "security definer" in definition
        assert "set search_path = pg_catalog, public, pg_temp" in definition
        assert "v_user is null" in definition
        assert "owner_id = v_user" in definition
        assert "current_doc.object_key is null" in definition


def test_version_object_keys_bind_owner_hash_and_safe_single_segment():
    assert "[a-za-z0-9-][a-za-z0-9._-]{0,254}$" in CANDIDATE
    assert "'/[^/]+$')" not in CANDIDATE
    assert "p_object_key !~ ('^users/' || v_user::text || '/documents/' || v_sha" in CANDIDATE
    assert "chosen.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(chosen.sha256)" in CANDIDATE
    assert "current_doc.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(current_doc.sha256)" in CANDIDATE


def test_execute_acl_is_authenticated_only_and_revokes_service_role():
    for signature in (
        "public.doka_bulk_update_documents(uuid[],text,text)",
        "public.doka_replace_document_version(uuid,text,text,text,bigint,text)",
        "public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text)",
        "public.doka_restore_document_version(uuid,uuid)",
    ):
        assert f"revoke all on function {signature} from public, anon, service_role;" in CANDIDATE
        assert f"grant execute on function {signature} to authenticated;" in CANDIDATE
    assert "to authenticated, service_role;" not in CANDIDATE

def test_storage_aware_rpc_rejects_mock_provider_in_cloud_database():
    definition = function_definition("doka_replace_document_version_storage")
    assert "p_storage_provider not in ('supabase', 'b2')" in definition
    assert "'mock'" not in definition


def test_restore_requires_ready_supported_storage_version():
    definition = function_definition("doka_restore_document_version")
    assert "chosen.storage_provider not in ('supabase', 'b2')" in definition
    assert "chosen.storage_status <> 'ready'" in definition
