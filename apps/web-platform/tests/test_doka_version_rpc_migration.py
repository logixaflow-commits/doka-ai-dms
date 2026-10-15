from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    REPO_ROOT / "supabase" / "migrations"
    / "20261002100658_doka_version_object_key_pattern.sql"
).read_text(encoding="utf-8")


def test_version_rpc_requires_authenticated_owner_and_fixed_search_path():
    assert "if auth.uid() is null then" in MIGRATION
    assert "set search_path = pg_catalog, public, pg_temp" in MIGRATION
    assert "owner_id = auth.uid()" in MIGRATION
    assert "from public, anon" in MIGRATION


def test_version_rpc_binds_object_key_to_user_sha_and_single_safe_segment():
    assert "'/documents/' || p_sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$'" in MIGRATION
    assert "'/documents/' || chosen.sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$'" in MIGRATION
    assert "position('/' in p_filename) > 0" in MIGRATION
    assert "position(chr(92) in p_filename) > 0" in MIGRATION
