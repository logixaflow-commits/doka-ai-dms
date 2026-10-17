from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "supabase"
    / "migrations"
    / "20261017100000_doka_rpc_security_hardening.sql"
).read_text(encoding="utf-8")


def function_definition(name: str) -> str:
    match = re.search(
        rf"CREATE OR REPLACE FUNCTION public\.{re.escape(name)}\(.*?\$function\$;",
        MIGRATION,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"missing migration definition for {name}"
    return match.group(0).lower()


def test_sensitive_rpcs_are_definer_with_fixed_search_path_and_owner_identity():
    for name in (
        "doka_bulk_update_documents",
        "doka_replace_document_version",
        "doka_replace_document_version_storage",
        "doka_restore_document_version",
    ):
        definition = function_definition(name)
        assert "security definer" in definition
        assert "set search_path = pg_catalog, public, pg_temp" in definition
        assert "auth.uid()" in definition
        assert "v_user is null" in definition
        assert "owner_id = v_user" in definition


def test_version_rpcs_bind_storage_keys_to_owner_and_content_hash():
    for name in (
        "doka_replace_document_version",
        "doka_replace_document_version_storage",
        "doka_restore_document_version",
    ):
        definition = function_definition(name)
        assert "'^users/' || v_user::text || '/documents/'" in definition
        assert "sha256" in definition
        assert "invalid version object metadata" in definition or "stored version metadata is invalid" in definition


def test_rpc_execution_acl_is_not_public_or_anon():
    for signature in (
        "public.doka_bulk_update_documents(uuid[],text,text)",
        "public.doka_replace_document_version(uuid,text,text,text,bigint,text)",
        "public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text)",
        "public.doka_restore_document_version(uuid,uuid)",
    ):
        assert f"revoke all on function {signature} from public, anon;" in MIGRATION.lower()
        assert f"grant execute on function {signature} to authenticated, service_role;" in MIGRATION.lower()


def test_bulk_rpc_limits_count_and_actions_before_mutation():
    definition = function_definition("doka_bulk_update_documents")
    assert "cardinality(p_document_ids) < 1" in definition
    assert "cardinality(p_document_ids) > 100" in definition
    assert "p_action not in ('status', 'trash')" in definition
    assert "matched_count <> cardinality(p_document_ids)" in definition
