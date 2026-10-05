from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (REPO_ROOT / "supabase" / "migrations" / "20261005120000_doka_storage_provider_metadata.sql").read_text(encoding="utf-8")
ROLLBACK = (REPO_ROOT / "docs" / "DOKA_STORAGE_MIGRATION_ROLLBACK.md").read_text(encoding="utf-8")


def test_existing_documents_default_to_supabase_without_storage_byte_operations():
    assert "storage_provider text not null default 'supabase'" in MIGRATION
    assert "storage_provider = 'supabase'" in MIGRATION
    assert "/storage/v1/" not in MIGRATION
    assert "copy(" not in MIGRATION.lower()
    assert "delete from storage" not in MIGRATION.lower()
    assert "insert into storage.objects" not in MIGRATION.lower()


def test_provider_and_status_constraints_are_explicit_and_source_provider_safe():
    assert "storage_provider in ('supabase', 'b2', 'mock')" in MIGRATION
    assert "storage_status in ('pending', 'uploading', 'ready', 'quarantined', 'failed', 'deleting')" in MIGRATION
    assert "preview_provider is null or preview_provider in ('cloudinary', 'supabase', 'mock')" in MIGRATION
    assert "export_provider is null or export_provider in ('google_drive')" in MIGRATION


def test_rollback_is_routing_only_and_preserves_supabase_objects():
    assert "STORAGE_PROVIDER=supabase" in ROLLBACK
    assert "must never delete the original Supabase object" in ROLLBACK
    assert "No byte copy is required" in ROLLBACK
