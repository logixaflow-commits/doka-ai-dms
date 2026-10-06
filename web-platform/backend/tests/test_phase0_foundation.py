"""Automated regression coverage for the Personal Local Phase 0 foundation.

These tests cover deterministic parts of PL-G4, PL-G7, PL-G12/13, PL-G14,
and the core local safety/auth boundaries. Real Windows/UI/OCR/office-dataset
gates remain explicit acceptance tests and are not falsely marked passed here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.local_security import (
    consume_local_refresh_token,
    create_local_access_token,
    create_local_refresh_token,
    decode_local_token,
    invalidate_local_token,
)
from app.services.safe_workspace_service import safe_workspace_service, sha256_file
from app.services.workspace_backup_service import workspace_backup_service


@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    auth_state = tmp_path / "auth" / "local_auth_state.sqlite3"
    source.mkdir()

    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "FINAL_ROOT", workspace / "Final")
    monkeypatch.setattr(settings, "QUARANTINE_ROOT", workspace / "Quarantine")
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", auth_state)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "phase0-test-secret-key-with-more-than-32-bytes")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    return source, workspace, backups


def test_phase0_safety_defaults_are_fail_closed():
    assert settings.ORIGINAL_READ_ONLY is True
    assert settings.ALLOW_SOURCE_WRITE is False
    assert isinstance(settings.AI_ENABLED, bool)


def test_safe_import_preserves_source_and_records_sha256(isolated_workspace):
    source, workspace, _ = isolated_workspace
    first = source / "invoice.txt"
    second = source / "notes.txt"
    first.write_text("invoice 123", encoding="utf-8")
    second.write_text("meeting notes", encoding="utf-8")
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}

    created = safe_workspace_service.create_import()
    completed = safe_workspace_service.run_import(created["session_id"])

    assert completed["state"] in {"completed", "completed_with_errors"}
    manifest = json.loads(
        (workspace / "imports" / created["session_id"] / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["files"]["invoice.txt"]["verified"] is True
    assert manifest["files"]["invoice.txt"]["sha256"] == before["invoice.txt"]
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()} == before


def test_scan_detects_exact_duplicates_and_searches_inventory(isolated_workspace):
    source, _, _ = isolated_workspace
    (source / "a.txt").write_text("same content", encoding="utf-8")
    (source / "b.txt").write_text("same content", encoding="utf-8")
    (source / "unique.txt").write_text("unique searchable phrase", encoding="utf-8")

    created = safe_workspace_service.create_import()
    safe_workspace_service.run_import(created["session_id"])
    scanned = safe_workspace_service.scan(created["session_id"])

    assert scanned["exact_duplicate_groups"] == 1
    assert scanned["exact_duplicate_files"] == 2

    result = safe_workspace_service.search(created["session_id"], "unique searchable")
    assert result["total_matches"] == 1
    assert result["results"][0]["filename"] == "unique.txt"


def test_backup_verify_and_restore_are_integrity_checked(isolated_workspace):
    _, workspace, _ = isolated_workspace
    target = workspace / "Final" / "approved.txt"
    target.parent.mkdir(parents=True)
    target.write_text("approved document", encoding="utf-8")
    expected = sha256_file(target)

    manifest = workspace_backup_service.create()
    archive_name = Path(manifest["archive"]).name
    verified = workspace_backup_service.verify(archive_name)
    assert verified["verified"] is True
    assert verified["sha256"] == manifest["sha256"]

    restored = workspace_backup_service.restore_to_recovery(archive_name, confirm=True)
    restored_file = Path(restored["recovery_path"]) / "Final" / "approved.txt"
    assert restored["active_workspace_changed"] is False
    assert restored_file.is_file()
    assert sha256_file(restored_file) == expected


def test_local_session_refresh_rotation_and_logout_are_persistent(isolated_workspace):
    session_id = "phase0-session"
    access = create_local_access_token("admin", session_id)
    refresh = create_local_refresh_token("admin", session_id)

    assert decode_local_token(access)["sub"] == "admin"
    assert consume_local_refresh_token(refresh) is not None
    assert consume_local_refresh_token(refresh) is None
    assert invalidate_local_token(access) is True
    assert decode_local_token(access) is None


def test_source_root_cannot_overlap_writable_workspace(isolated_workspace, monkeypatch):
    source, _, _ = isolated_workspace
    monkeypatch.setattr(settings, "WORKING_ROOT", source / "nested")
    with pytest.raises(ValueError, match="overlap"):
        safe_workspace_service.validate_source(source)
