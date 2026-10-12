from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "cloudflare_worker" / "migrations"


def _database_with_migrations() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    for migration in sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        connection.executescript(migration.read_text(encoding="utf-8"))
    return connection


def _seed_organization(connection: sqlite3.Connection) -> None:
    connection.execute("INSERT INTO users (id, email) VALUES ('owner', 'owner@example.invalid')")
    connection.execute("INSERT INTO users (id, email) VALUES ('member', 'member@example.invalid')")
    connection.execute("INSERT INTO users (id, email) VALUES ('outsider', 'outsider@example.invalid')")
    connection.execute(
        "INSERT INTO organizations (id, name, created_by) VALUES ('org', 'Doka Test Org', 'owner')"
    )
    connection.execute(
        "INSERT INTO organization_members (organization_id, user_id, role) VALUES ('org', 'owner', 'owner')"
    )
    connection.execute(
        "INSERT INTO organization_members (organization_id, user_id, role) VALUES ('org', 'member', 'member')"
    )


def _insert_document(connection: sqlite3.Connection, *, owner: str, doc_id: str = "doc") -> None:
    connection.execute(
        """INSERT INTO documents
           (id, owner_id, organization_id, object_key, filename, size_bytes, sha256)
           VALUES (?, ?, 'org', ?, 'test.txt', 1, ?)""",
        (doc_id, owner, f"org/{doc_id}.txt", "a" * 64),
    )


def test_all_numbered_d1_migrations_apply_cleanly_in_sqlite():
    connection = _database_with_migrations()
    objects = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'index', 'trigger')"
        )
    }
    assert "organization_one_owner_idx" in objects
    assert "documents_owner_must_be_org_member_insert" in objects
    assert "document_permissions_scope_insert" in objects
    assert "jobs_require_organization_insert" in objects
    assert "jobs_require_organization_update" in objects
    connection.close()


def test_organization_can_have_only_one_owner():
    connection = _database_with_migrations()
    _seed_organization(connection)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO organization_members (organization_id, user_id, role) VALUES ('org', 'outsider', 'owner')"
        )
    connection.close()


def test_organization_document_owner_must_be_a_member():
    connection = _database_with_migrations()
    _seed_organization(connection)
    with pytest.raises(sqlite3.IntegrityError, match="document owner must be an organization member"):
        _insert_document(connection, owner="outsider")
    _insert_document(connection, owner="member")
    connection.close()


def test_permission_recipient_and_granter_must_be_authorized():
    connection = _database_with_migrations()
    _seed_organization(connection)
    _insert_document(connection, owner="member")
    with pytest.raises(sqlite3.IntegrityError, match="permission recipient must be an organization member"):
        connection.execute(
            "INSERT INTO document_permissions (document_id, user_id, permission, granted_by) VALUES ('doc', 'outsider', 'read', 'owner')"
        )
    with pytest.raises(sqlite3.IntegrityError, match="permission grant requires document owner or organization admin"):
        connection.execute(
            "INSERT INTO document_permissions (document_id, user_id, permission, granted_by) VALUES ('doc', 'owner', 'read', 'outsider')"
        )
    connection.execute(
        "INSERT INTO document_permissions (document_id, user_id, permission, granted_by) VALUES ('doc', 'owner', 'read', 'member')"
    )
    connection.close()



def test_durable_jobs_require_a_nonblank_organization():
    connection = _database_with_migrations()
    _seed_organization(connection)
    connection.execute(
        """INSERT INTO jobs (id, organization_id, job_type, idempotency_key, payload_json)
           VALUES ('job-valid', 'org', 'ocr', 'key-valid', '{}')"""
    )
    for job_id, organization_id, key in (
        ("job-null", None, "key-null"),
        ("job-blank", "", "key-blank"),
        ("job-space", "   ", "key-space"),
        ("job-padded", " org ", "key-padded"),
    ):
        with pytest.raises(sqlite3.IntegrityError, match="durable jobs require an organization"):
            connection.execute(
                """INSERT INTO jobs (id, organization_id, job_type, idempotency_key, payload_json)
                   VALUES (?, ?, 'ocr', ?, '{}')""",
                (job_id, organization_id, key),
            )
    for invalid_org in (None, "", "   ", " org "):
        with pytest.raises(sqlite3.IntegrityError, match="durable jobs require an organization"):
            connection.execute(
                "UPDATE jobs SET organization_id = ? WHERE id = 'job-valid'",
                (invalid_org,),
            )
    connection.close()
