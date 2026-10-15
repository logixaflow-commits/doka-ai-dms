"""Executable authorization-integrity tests for the D1 Cloud schema."""
from pathlib import Path
import sqlite3

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "cloudflare_worker" / "migrations" / "0001_doka_cloud_baseline.sql"
AUTHZ = ROOT / "cloudflare_worker" / "migrations" / "0002_authorization_integrity.sql"
HASH = "a" * 64


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(BASELINE.read_text(encoding="utf-8"))
    connection.executescript(AUTHZ.read_text(encoding="utf-8"))
    yield connection
    connection.close()


def seed_user(db, user_id):
    db.execute(
        "INSERT INTO users(id, email) VALUES (?, ?)",
        (user_id, f"{user_id}@example.test"),
    )


def seed_org(db, org_id="org-1", owner_id="owner-1"):
    db.execute(
        "INSERT INTO organizations(id, name, created_by) VALUES (?, ?, ?)",
        (org_id, "Example Org", owner_id),
    )
    db.execute(
        "INSERT INTO organization_members(organization_id, user_id, role) VALUES (?, ?, 'owner')",
        (org_id, owner_id),
    )


def seed_document(db, document_id="doc-1", owner_id="owner-1", org_id="org-1"):
    db.execute(
        """
        INSERT INTO documents(
            id, owner_id, organization_id, object_key, filename, size_bytes, sha256
        ) VALUES (?, ?, ?, ?, 'sample.pdf', 12, ?)
        """,
        (document_id, owner_id, org_id, f"documents/{org_id}/{document_id}", HASH),
    )


def test_org_document_requires_owner_membership(db):
    seed_user(db, "owner-1")
    seed_org(db)
    seed_user(db, "outsider")

    with pytest.raises(sqlite3.IntegrityError, match="owner must be an organization member"):
        seed_document(db, owner_id="outsider")


def test_org_allows_only_one_owner_role(db):
    seed_user(db, "owner-1")
    seed_user(db, "owner-2")
    seed_org(db)

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO organization_members(organization_id, user_id, role)
            VALUES ('org-1', 'owner-2', 'owner')
            """
        )


def test_org_document_permission_recipient_must_be_member(db):
    seed_user(db, "owner-1")
    seed_user(db, "outsider")
    seed_org(db)
    seed_document(db)

    with pytest.raises(sqlite3.IntegrityError, match="recipient must be an organization member"):
        db.execute(
            """
            INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
            VALUES ('doc-1', 'outsider', 'read', 'owner-1')
            """
        )


def test_org_document_permission_granter_must_be_owner_or_admin(db):
    seed_user(db, "owner-1")
    seed_user(db, "member-1")
    seed_user(db, "viewer-1")
    seed_org(db)
    db.execute(
        """
        INSERT INTO organization_members(organization_id, user_id, role)
        VALUES ('org-1', 'member-1', 'member')
        """
    )
    db.execute(
        """
        INSERT INTO organization_members(organization_id, user_id, role)
        VALUES ('org-1', 'viewer-1', 'viewer')
        """
    )
    seed_document(db)

    with pytest.raises(sqlite3.IntegrityError, match="permission grant requires"):
        db.execute(
            """
            INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
            VALUES ('doc-1', 'member-1', 'read', 'viewer-1')
            """
        )

    db.execute(
        """
        INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
        VALUES ('doc-1', 'member-1', 'read', 'owner-1')
        """
    )


def test_admin_can_grant_org_document_permission(db):
    seed_user(db, "owner-1")
    seed_user(db, "admin-1")
    seed_user(db, "member-1")
    seed_org(db)
    db.execute(
        """
        INSERT INTO organization_members(organization_id, user_id, role)
        VALUES ('org-1', 'admin-1', 'admin')
        """
    )
    db.execute(
        """
        INSERT INTO organization_members(organization_id, user_id, role)
        VALUES ('org-1', 'member-1', 'member')
        """
    )
    seed_document(db)

    db.execute(
        """
        INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
        VALUES ('doc-1', 'member-1', 'write', 'admin-1')
        """
    )
    assert db.execute(
        "SELECT permission FROM document_permissions WHERE document_id = 'doc-1' AND user_id = 'member-1'"
    ).fetchone()[0] == "write"


def test_personal_document_permissions_remain_owner_granted(db):
    seed_user(db, "owner-1")
    seed_user(db, "recipient-1")
    db.execute(
        """
        INSERT INTO documents(
            id, owner_id, object_key, filename, size_bytes, sha256
        ) VALUES ('personal-1', 'owner-1', 'documents/owner-1/personal-1',
                  'sample.pdf', 12, ?)
        """,
        (HASH,),
    )

    db.execute(
        """
        INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
        VALUES ('personal-1', 'recipient-1', 'read', 'owner-1')
        """
    )

    with pytest.raises(sqlite3.IntegrityError, match="permission grant requires"):
        db.execute(
            """
            INSERT INTO document_permissions(document_id, user_id, permission, granted_by)
            VALUES ('personal-1', 'owner-1', 'write', 'recipient-1')
            """
        )
