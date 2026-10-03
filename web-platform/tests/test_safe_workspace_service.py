import threading
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


def test_list_sessions_rejects_symlinked_imports_root(tmp_path, monkeypatch, make_symlink):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / ("a" * 32)).mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    make_symlink(workspace / "imports", outside, target_is_directory=True)

    with pytest.raises(ValueError, match="Import sessions directory cannot be a symlink"):
        SafeWorkspaceService().list_sessions()


def test_list_sessions_rejects_symlinked_session_directory(tmp_path, monkeypatch, make_symlink):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    (workspace / "imports").mkdir(parents=True)
    outside.mkdir()
    (outside / "status.json").write_text('{"state":"outside"}', encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    make_symlink(
        workspace / "imports" / ("a" * 32),
        outside,
        target_is_directory=True,
    )

    with pytest.raises(ValueError, match="Import session directory cannot be a symlink"):
        SafeWorkspaceService().list_sessions()


@pytest.mark.parametrize(
    ("metadata_name", "reader"),
    [
        ("status.json", "status"),
        ("manifest.json", "manifest"),
        ("inventory.json", "inventory"),
        ("understanding.json", "understanding"),
    ],
)
def test_readers_reject_symlinked_session_metadata(
    tmp_path, monkeypatch, make_symlink, metadata_name, reader
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside.json"
    workspace.mkdir()
    source.mkdir()
    outside.write_text('{"state":"outside","results":[]}', encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    session = service.create_import()
    service.run_import(session["session_id"])
    service.scan(session["session_id"])
    service._write(
        service._json_path(session["session_id"], "understanding.json"),
        {"results": []},
    )
    metadata = service._dir(session["session_id"]) / metadata_name
    metadata.unlink()
    make_symlink(metadata, outside)

    with pytest.raises(ValueError, match="metadata file cannot be a symlink"):
        if reader == "status":
            service.status(session["session_id"])
        elif reader == "manifest":
            service._read(service._json_path(session["session_id"], metadata_name))
        elif reader == "inventory":
            service.inventory(session["session_id"])
        else:
            service.get_understanding(session["session_id"])


def test_write_rejects_symlinked_temporary_metadata_file(
    tmp_path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside.json"
    workspace.mkdir()
    source.mkdir()
    outside.write_text('{"state":"unchanged"}', encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    session = service.create_import()
    status_path = service._json_path(session["session_id"], "status.json")
    make_symlink(status_path.with_suffix(".json.tmp"), outside)

    with pytest.raises(ValueError, match="Temporary import metadata file cannot be a symlink"):
        service._write(status_path, {"state": "changed"})
    assert outside.read_text(encoding="utf-8") == '{"state":"unchanged"}'


def test_metadata_read_and_write_reject_paths_outside_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.json"
    workspace.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    outside.write_text('{"state":"unchanged"}', encoding="utf-8")
    service = SafeWorkspaceService()

    with pytest.raises(ValueError, match="outside the workspace"):
        service._read(outside)
    with pytest.raises(ValueError, match="outside the workspace"):
        service._write(outside, {"state": "changed"})
    assert outside.read_text(encoding="utf-8") == '{"state":"unchanged"}'


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


@pytest.mark.parametrize(
    "reader", ["status", "list_sessions", "search", "inventory", "understanding"]
)
def test_session_state_readers_wait_for_mutations(tmp_path, monkeypatch, reader):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    session = service.create_import()
    service.run_import(session["session_id"])
    service.scan(session["session_id"])
    service._write(
        service._json_path(session["session_id"], "understanding.json"),
        {"results": []},
    )
    lock = service._lock(session["session_id"])
    read_started = threading.Event()
    read_finished = threading.Event()
    errors = []
    original_read = service._read

    def tracked_read(path):
        read_started.set()
        return original_read(path)

    def read_status():
        try:
            if reader == "status":
                service.status(session["session_id"])
            elif reader == "list_sessions":
                service.list_sessions()
            elif reader == "search":
                service.search(session["session_id"], "")
            elif reader == "inventory":
                service.inventory(session["session_id"])
            else:
                service.get_understanding(session["session_id"])
        except Exception as exc:
            errors.append(exc)
        finally:
            read_finished.set()

    monkeypatch.setattr(service, "_read", tracked_read)
    lock.acquire()
    try:
        thread = threading.Thread(target=read_status)
        thread.start()
        assert not read_started.wait(timeout=1)
    finally:
        lock.release()

    assert read_started.wait(timeout=1)
    assert read_finished.wait(timeout=1)
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert not errors


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


def test_search_filters_extension_and_review(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    (source / "invoice.pdf").write_text("invoice", encoding="utf-8")
    (source / "notes.txt").write_text("notes", encoding="utf-8")

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    service.run_import(created["session_id"])
    service.scan(created["session_id"])

    assert service.search(created["session_id"], "invoice", extension=".pdf")["total"] == 1
    assert service.search(created["session_id"], "invoice", extension=".txt")["total"] == 0



def test_source_write_flag_is_rejected_even_if_read_only_flag_is_disabled(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", False)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", True)
    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="ALLOW_SOURCE_WRITE"):
        service.validate_source(source)



def test_import_rejects_symlinked_source_copy_root(tmp_path, monkeypatch, make_symlink):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source.mkdir()
    outside.mkdir()
    (source / "file.txt").write_text("source", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    session = service.create_import()
    copy_root = workspace / "imports" / session["session_id"] / "source_copy"
    make_symlink(copy_root, outside, target_is_directory=True)

    with pytest.raises(ValueError, match="working-copy directory cannot be a symlink"):
        service.run_import(session["session_id"])
    assert not list(outside.iterdir())


def test_import_does_not_follow_symlinked_destination_parent(
    tmp_path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    (source / "nested").mkdir(parents=True)
    outside.mkdir()
    (source / "nested" / "file.txt").write_text("source", encoding="utf-8")
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    session = service.create_import()
    copy_root = workspace / "imports" / session["session_id"] / "source_copy"
    copy_root.mkdir()
    make_symlink(copy_root / "nested", outside, target_is_directory=True)

    result = service.run_import(session["session_id"])
    assert result["files_failed"] == 1
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert not (outside / "file.txt").exists()


def test_source_requires_original_read_only_flag(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", False)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="ORIGINAL_READ_ONLY"):
        SafeWorkspaceService().validate_source(source)
