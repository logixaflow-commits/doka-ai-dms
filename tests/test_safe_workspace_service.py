from pathlib import Path

import pytest

from app.core.config import settings
from app.services.safe_workspace_service import SafeWorkspaceService, sha256_file


def test_sha256_file(tmp_path: Path):
    file = tmp_path / "hello.txt"
    file.write_bytes(b"hello")
    assert sha256_file(file) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_source_cannot_overlap_workspace(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = workspace / "source"
    source.mkdir(parents=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="overlap"):
        service.validate_source(source)


def test_source_outside_workspace_is_allowed(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    service = SafeWorkspaceService()
    assert service.validate_source(source) == source.resolve()


def test_safe_import_scan_search_and_resume(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    (source / "invoice.txt").write_text("Invoice INV-001 for shipping", encoding="utf-8")
    original = (source / "invoice.txt").read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    completed = service.run_import(created["session_id"])
    assert completed["state"] == "completed"

    inventory = service.scan(created["session_id"])
    assert inventory["files_total"] == 1

    results = service.search(created["session_id"], "invoice")
    assert results["total"] == 1

    assert (source / "invoice.txt").read_bytes() == original
    listed = service.list_sessions()
    assert listed[0]["session_id"] == created["session_id"]
    assert listed[0]["state"] == "scanned"


def test_search_total_counts_matches_beyond_limit(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    for index in range(3):
        (source / f"invoice-{index}.txt").write_text("invoice shipping", encoding="utf-8")

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    service.run_import(created["session_id"])
    service.scan(created["session_id"])

    results = service.search(created["session_id"], "invoice", limit=1)
    assert results["total"] == 3
    assert len(results["results"]) == 1
