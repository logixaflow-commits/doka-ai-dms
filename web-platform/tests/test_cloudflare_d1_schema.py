"""Executable SQLite contract tests for the Cloudflare D1 baseline schema.

SQLite is used here to validate the D1-compatible schema offline. This does not
replace a remote D1 migration/integration test.
"""
from pathlib import Path
import sqlite3

import pytest


ROOT = Path(__file__).resolve().parents[2]
D1_MIGRATION = ROOT / "cloudflare_worker" / "migrations" / "0001_doka_cloud_baseline.sql"
TURSO_MIGRATION = ROOT / "cloudflare_worker" / "turso_migrations" / "0001_sync_receipts.sql"
VALID_HASH = "a" * 64


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(D1_MIGRATION.read_text(encoding="utf-8"))
    yield connection
    connection.close()


def seed_user(db, user_id="user-1"):
    db.execute(
        "INSERT INTO users(id, email) VALUES (?, ?)",
        (user_id, f"{user_id}@example.test"),
    )


def seed_document(db, document_id="doc-1", owner_id="user-1", object_key="documents/user-1/doc-1"):
    db.execute(
        """
        INSERT INTO documents(
            id, owner_id, object_key, filename, size_bytes, sha256
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, owner_id, object_key, "sample.pdf", 12, VALID_HASH),
    )


def test_d1_migration_creates_expected_cloud_tables_and_indexes(db):
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "users", "organizations", "organization_members", "documents",
        "document_versions", "document_permissions", "document_chunks",
        "audit_events", "jobs", "outbox_events",
    } <= tables

    indexes = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
    }
    assert {
        "documents_owner_created_idx",
        "document_versions_document_created_idx",
        "audit_events_owner_created_idx",
        "jobs_status_available_idx",
        "outbox_events_pending_idx",
    } <= indexes


def test_document_requires_existing_owner_and_valid_metadata(db):
    with pytest.raises(sqlite3.IntegrityError):
        seed_document(db)

    seed_user(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO documents(id, owner_id, object_key, filename, size_bytes, sha256)
            VALUES ('bad', 'user-1', 'documents/bad', 'bad.pdf', -1, ?)
            """,
            (VALID_HASH,),
        )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO documents(id, owner_id, object_key, filename, size_bytes, sha256)
            VALUES ('bad-hash', 'user-1', 'documents/bad-hash', 'bad.pdf', 1, 'not-a-hash')
            """
        )


def test_document_paths_and_status_are_constrained(db):
    seed_user(db)
    for index, (object_key, folder_path, status) in enumerate((
        ("../escape", "/", "active"),
        ("documents/ok", "/../escape", "active"),
        ("documents/ok", "/", "unknown"),
    )):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO documents(
                    id, owner_id, object_key, filename, size_bytes, sha256, folder_path, status
                ) VALUES (?, 'user-1', ?, 'sample.pdf', 1, ?, ?, ?)
                """,
                (f"bad-{index}", object_key, VALID_HASH, folder_path, status),
            )


def test_document_and_version_keys_are_unique_and_version_numbers_are_positive(db):
    seed_user(db)
    seed_document(db)
    with pytest.raises(sqlite3.IntegrityError):
        seed_document(db, "doc-2", object_key="documents/user-1/doc-1")

    db.execute(
        """
        INSERT INTO document_versions(
            id, document_id, version_no, object_key, filename, size_bytes, sha256
        ) VALUES ('version-1', 'doc-1', 1, 'documents/user-1/doc-1/v1', 'sample.pdf', 12, ?)
        """,
        (VALID_HASH,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO document_versions(
                id, document_id, version_no, object_key, filename, size_bytes, sha256
            ) VALUES ('version-bad', 'doc-1', 0, 'documents/user-1/doc-1/v0', 'sample.pdf', 12, ?)
            """,
            (VALID_HASH,),
        )


def test_document_delete_cascades_versions_and_preserves_audit_event(db):
    seed_user(db)
    seed_document(db)
    db.execute(
        """
        INSERT INTO document_versions(
            id, document_id, version_no, object_key, filename, size_bytes, sha256
        ) VALUES ('version-1', 'doc-1', 1, 'documents/user-1/doc-1/v1', 'sample.pdf', 12, ?)
        """,
        (VALID_HASH,),
    )
    db.execute(
        """
        INSERT INTO audit_events(id, owner_id, document_id, action)
        VALUES ('audit-1', 'user-1', 'doc-1', 'upload')
        """
    )

    db.execute("DELETE FROM documents WHERE id = 'doc-1'")

    assert db.execute("SELECT count(*) FROM document_versions").fetchone()[0] == 0
    assert db.execute(
        "SELECT document_id FROM audit_events WHERE id = 'audit-1'"
    ).fetchone()[0] == "doc-1"


def test_document_chunks_must_reference_a_version_of_the_same_document(db):
    seed_user(db)
    seed_document(db, "doc-1", object_key="documents/user-1/doc-1")
    seed_document(db, "doc-2", object_key="documents/user-1/doc-2")
    db.execute(
        """
        INSERT INTO document_versions(
            id, document_id, version_no, object_key, filename, size_bytes, sha256
        ) VALUES ('version-1', 'doc-1', 1, 'documents/user-1/doc-1/v1', 'sample.pdf', 12, ?)
        """,
        (VALID_HASH,),
    )

    with pytest.raises(sqlite3.IntegrityError, match="version mismatch"):
        db.execute(
            """
            INSERT INTO document_chunks(
                id, document_id, version_id, chunk_index, content, content_sha256
            ) VALUES ('chunk-bad', 'doc-2', 'version-1', 0, 'private text', ?)
            """,
            (VALID_HASH,),
        )

    db.execute(
        """
        INSERT INTO document_chunks(
            id, document_id, version_id, chunk_index, content, content_sha256
        ) VALUES ('chunk-1', 'doc-1', 'version-1', 0, 'private text', ?)
        """,
        (VALID_HASH,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO document_chunks(
                id, document_id, version_id, chunk_index, content, content_sha256
            ) VALUES ('chunk-duplicate', 'doc-1', 'version-1', 0, 'duplicate', ?)
            """,
            (VALID_HASH,),
        )


def test_audit_events_are_append_only(db):
    seed_user(db)
    db.execute(
        "INSERT INTO audit_events(id, owner_id, action) VALUES ('audit-1', 'user-1', 'upload')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("UPDATE audit_events SET action = 'download' WHERE id = 'audit-1'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("DELETE FROM audit_events WHERE id = 'audit-1'")


def test_jobs_and_outbox_events_require_unique_idempotency_keys(db):
    db.execute(
        """
        INSERT INTO jobs(id, job_type, idempotency_key, payload_json)
        VALUES ('job-1', 'ocr', 'job:doc-1:v1', '{"document_id":"doc-1"}')
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO jobs(id, job_type, idempotency_key, payload_json)
            VALUES ('job-2', 'ocr', 'job:doc-1:v1', '{"document_id":"doc-1"}')
            """
        )

    db.execute(
        """
        INSERT INTO outbox_events(
            id, event_type, aggregate_type, aggregate_id, idempotency_key, payload_json
        ) VALUES ('event-1', 'document.created', 'document', 'doc-1',
                  'document.created:doc-1', '{"document_id":"doc-1"}')
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO outbox_events(
                id, event_type, aggregate_type, aggregate_id, idempotency_key, payload_json
            ) VALUES ('event-2', 'document.created', 'document', 'doc-1',
                      'document.created:doc-1', '{"document_id":"doc-1"}')
            """
        )


def test_turso_receipt_migration_supports_idempotent_event_application():
    connection = sqlite3.connect(":memory:")
    connection.executescript(TURSO_MIGRATION.read_text(encoding="utf-8"))
    connection.execute("INSERT INTO sync_receipts(event_id) VALUES ('event-1')")
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO sync_receipts(event_id) VALUES ('event-1')")
    connection.close()
