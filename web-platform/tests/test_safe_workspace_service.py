import multiprocessing
import os
import threading
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.safe_workspace_service import (
    SafeWorkspaceService,
    SessionOperationInProgress,
    sha256_file,
)


def _process_workspace(path):
    settings.WORKING_ROOT = Path(path)


def _process_hold_operation(workspace, session_id, ready, release, result):
    _process_workspace(workspace)
    try:
        with SafeWorkspaceService()._session_operation(session_id, "process-test"):
            result.put("acquired")
            ready.set()
            if not release.wait(timeout=10):
                result.put("hold-timeout")
    except SessionOperationInProgress:
        result.put("conflict")
        ready.set()
    except Exception as exc:
        result.put(("error", repr(exc)))
        ready.set()


def _process_update_status(workspace, session_id, field, barrier, result):
    _process_workspace(workspace)
    try:
        barrier.wait(timeout=10)
        SafeWorkspaceService()._update_status(session_id, {field: True})
        result.put("updated")
    except Exception as exc:
        result.put(("error", repr(exc)))


def _process_exit_with_operation(workspace, session_id, acquired):
    _process_workspace(workspace)
    with SafeWorkspaceService()._session_operation(session_id, "crash-test"):
        acquired.set()
        os._exit(0)


def _process_write_status(workspace, session_id, marker, barrier, result):
    _process_workspace(workspace)
    service = SafeWorkspaceService()
    status_path = service._json_path(session_id, "status.json")
    try:
        barrier.wait(timeout=10)
        for sequence in range(30):
            service._write(status_path, {
                "marker": marker,
                "sequence": sequence,
                "payload": marker * 16384,
            })
        result.put("written")
    except Exception as exc:
        result.put(("error", repr(exc)))


def test_sha256_file(tmp_path: Path):
    file = tmp_path / "hello.txt"
    file.write_bytes(b"hello")
    assert sha256_file(file) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_source_cannot_overlap_workspace(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = workspace / "source"
    source.mkdir(parents=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="overlap"):
        service.validate_source(source)


def test_overlapping_workspace_validation_does_not_create_workspace(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "source"
    workspace = source / "not-created-workspace"
    source.mkdir()
    original_file = source / "existing.txt"
    original_file.write_bytes(b"Synthetic source data")
    original_contents = {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="overlap"):
        SafeWorkspaceService().validate_source()

    assert not workspace.exists()
    assert {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    } == original_contents


def test_source_outside_workspace_is_allowed(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    service = SafeWorkspaceService()
    assert service.validate_source(source) == source.resolve()


def test_source_root_and_child_are_accepted(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    child = source_root / "Department-A"
    workspace.mkdir()
    child.mkdir(parents=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    service = SafeWorkspaceService()

    assert service.validate_source() == source_root.resolve()
    assert service.validate_source(child) == child.resolve()


def test_source_outside_configured_root_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source_root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().validate_source(outside)


def test_missing_source_root_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="SOURCE_ROOT is not configured"):
        SafeWorkspaceService().validate_source()


@pytest.mark.parametrize("invalid_root_type", ["missing", "file"])
def test_invalid_source_root_is_rejected(
    tmp_path: Path, monkeypatch, invalid_root_type
):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    workspace.mkdir()
    if invalid_root_type == "file":
        source_root.write_text("synthetic non-directory root", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="Configured source root is invalid"):
        SafeWorkspaceService().validate_source()


def test_invalid_source_candidate_file_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    workspace.mkdir()
    source_root.mkdir()
    source_file = source_root / "not-a-directory.txt"
    source_file.write_text("synthetic file", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="Source directory is invalid"):
        SafeWorkspaceService().validate_source(source_file)


def test_source_sibling_with_similar_prefix_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "Source"
    sibling = tmp_path / "Source-Outside"
    workspace.mkdir()
    source_root.mkdir()
    sibling.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().validate_source(sibling)


def test_source_traversal_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source_root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    traversal = source_root / ".." / "outside"
    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().validate_source(traversal)


def test_source_absolute_path_outside_root_is_rejected(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source_root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().validate_source(outside.resolve())


def test_source_symlink_escape_is_rejected(
    tmp_path: Path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source_root.mkdir()
    outside.mkdir()
    link = source_root / "linked-outside"
    make_symlink(link, outside, target_is_directory=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().validate_source(link)


def test_missing_source_is_rejected_without_disclosing_absolute_path(
    tmp_path: Path, monkeypatch
):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    missing = source_root / "missing"
    workspace.mkdir()
    source_root.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="Source directory is invalid") as exc_info:
        SafeWorkspaceService().validate_source(missing)
    assert str(missing) not in str(exc_info.value)


def test_create_import_rejects_source_override_outside_configured_root(
    tmp_path: Path, monkeypatch
):
    workspace = tmp_path / "workspace"
    source_root = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source_root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="outside the configured source root"):
        SafeWorkspaceService().create_import(str(outside))


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
    copied_file = (
        workspace / "imports" / created["session_id"] / "source_copy" / "invoice.txt"
    )
    assert copied_file.read_bytes() == original
    listed = service.list_sessions()
    assert listed[0]["session_id"] == created["session_id"]
    assert listed[0]["state"] == "scanned"


def test_safe_import_copies_nested_files_and_preserves_source(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    nested = source / "Department-A"
    workspace.mkdir()
    nested.mkdir(parents=True)
    source_file = nested / "invoice.txt"
    source_file.write_text("Synthetic nested import", encoding="utf-8")
    original = source_file.read_bytes()
    original_mtime = source_file.stat().st_mtime_ns

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    result = service.run_import(created["session_id"])
    copied = (
        workspace
        / "imports"
        / created["session_id"]
        / "source_copy"
        / "Department-A"
        / "invoice.txt"
    )
    manifest = service._read(service._json_path(created["session_id"], "manifest.json"))

    assert result["state"] == "completed"
    assert copied.read_bytes() == original
    assert copied.stat().st_mtime_ns == original_mtime
    assert manifest["files"]["Department-A/invoice.txt"]["sha256"] == sha256_file(copied)
    assert source_file.read_bytes() == original
    workspace_files = {
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    }
    assert workspace_files == {
        f"imports/{created['session_id']}/.metadata.lock",
        f"imports/{created['session_id']}/.operation.lock",
        f"imports/{created['session_id']}/manifest.json",
        f"imports/{created['session_id']}/source_copy/Department-A/invoice.txt",
        f"imports/{created['session_id']}/status.json",
    }


def _prepare_destination_attack_import(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    source_file = source / "nested" / "invoice.txt"
    source_file.parent.mkdir(parents=True)
    workspace.mkdir()
    source_file.write_bytes(b"Synthetic source contents for destination security")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    copy_root = workspace / "imports" / created["session_id"] / "source_copy"
    copy_root.mkdir()
    destination = copy_root / "nested" / "invoice.txt"
    destination.parent.mkdir()
    return service, created, source_file, destination


def test_import_rejects_destination_hard_link_without_modifying_source(
    tmp_path, monkeypatch
):
    service, created, source_file, destination = _prepare_destination_attack_import(
        tmp_path, monkeypatch
    )
    source_bytes = source_file.read_bytes()
    source_digest = sha256_file(source_file)
    destination.hardlink_to(source_file)

    result = service.run_import(created["session_id"])

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert source_file.read_bytes() == source_bytes
    assert sha256_file(source_file) == source_digest
    assert destination.read_bytes() == source_bytes
    assert sha256_file(destination) == source_digest


def test_import_rejects_destination_symlink_to_source(
    tmp_path, monkeypatch, make_symlink
):
    service, created, source_file, destination = _prepare_destination_attack_import(
        tmp_path, monkeypatch
    )
    source_bytes = source_file.read_bytes()
    source_digest = sha256_file(source_file)
    make_symlink(destination, source_file)

    result = service.run_import(created["session_id"])

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert source_file.read_bytes() == source_bytes
    assert sha256_file(source_file) == source_digest
    assert destination.is_symlink()


def test_import_rejects_destination_symlink_to_outside_file(
    tmp_path, monkeypatch, make_symlink
):
    service, created, source_file, destination = _prepare_destination_attack_import(
        tmp_path, monkeypatch
    )
    outside_file = tmp_path / "outside.txt"
    outside_file.write_bytes(b"Synthetic outside sentinel")
    source_bytes = source_file.read_bytes()
    source_digest = sha256_file(source_file)
    outside_bytes = outside_file.read_bytes()
    outside_digest = sha256_file(outside_file)
    make_symlink(destination, outside_file)

    result = service.run_import(created["session_id"])

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert source_file.read_bytes() == source_bytes
    assert sha256_file(source_file) == source_digest
    assert outside_file.read_bytes() == outside_bytes
    assert sha256_file(outside_file) == outside_digest
    assert destination.is_symlink()


def test_import_rejects_destination_parent_replaced_by_symlink(
    tmp_path, monkeypatch, make_symlink
):
    service, created, source_file, destination = _prepare_destination_attack_import(
        tmp_path, monkeypatch
    )
    copy_root = destination.parents[1]
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_bytes(b"Synthetic outside sentinel")
    source_bytes = source_file.read_bytes()
    source_digest = sha256_file(source_file)
    sentinel_bytes = sentinel.read_bytes()
    sentinel_digest = sha256_file(sentinel)
    original_open = service._open_working_copy_file

    def replace_parent_before_open(copy_path, relative_path, *, create):
        (copy_root / "nested").rmdir()
        make_symlink(copy_root / "nested", outside, target_is_directory=True)
        return original_open(copy_path, relative_path, create=create)

    monkeypatch.setattr(service, "_open_working_copy_file", replace_parent_before_open)
    result = service.run_import(created["session_id"])

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert source_file.read_bytes() == source_bytes
    assert sha256_file(source_file) == source_digest
    assert sentinel.read_bytes() == sentinel_bytes
    assert sha256_file(sentinel) == sentinel_digest
    assert not (outside / "invoice.txt").exists()


def test_import_does_not_overwrite_preexisting_destination(tmp_path, monkeypatch):
    service, created, source_file, destination = _prepare_destination_attack_import(
        tmp_path, monkeypatch
    )
    preexisting_bytes = b"Synthetic pre-existing destination"
    destination.write_bytes(preexisting_bytes)
    source_bytes = source_file.read_bytes()
    source_digest = sha256_file(source_file)
    destination_digest = sha256_file(destination)

    result = service.run_import(created["session_id"])

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert source_file.read_bytes() == source_bytes
    assert sha256_file(source_file) == source_digest
    assert destination.read_bytes() == preexisting_bytes
    assert sha256_file(destination) == destination_digest


def test_import_rejects_file_replaced_by_outside_symlink_before_open(
    tmp_path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source.mkdir()
    outside.mkdir()
    source_file = source / "invoice.txt"
    source_file.write_text("Synthetic source content", encoding="utf-8")
    outside_file = outside / "private.txt"
    outside_file.write_text("Synthetic outside content", encoding="utf-8")
    outside_original = outside_file.read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    original_open = service._open_source_file

    def replace_before_open(selected_source, path):
        path.unlink()
        make_symlink(path, outside_file)
        return original_open(selected_source, path)

    monkeypatch.setattr(service, "_open_source_file", replace_before_open)
    created = service.create_import()
    result = service.run_import(created["session_id"])
    copied = workspace / "imports" / created["session_id"] / "source_copy" / "invoice.txt"

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert not copied.exists()
    assert outside_file.read_bytes() == outside_original
    workspace_files = {
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    }
    assert workspace_files == {
        f"imports/{created['session_id']}/manifest.json",
        f"imports/{created['session_id']}/status.json",
    }


def test_import_rejects_parent_directory_replaced_by_outside_symlink(
    tmp_path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    department = source / "Department-A"
    outside = tmp_path / "outside"
    workspace.mkdir()
    department.mkdir(parents=True)
    outside.mkdir()
    (department / "invoice.txt").write_text("Synthetic source content", encoding="utf-8")
    outside_file = outside / "private.txt"
    outside_file.write_text("Synthetic outside content", encoding="utf-8")
    outside_original = outside_file.read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    original_open = service._open_source_file

    def replace_parent_before_open(selected_source, path):
        department.rename(source / "Department-A-held")
        make_symlink(department, outside, target_is_directory=True)
        return original_open(selected_source, path)

    monkeypatch.setattr(service, "_open_source_file", replace_parent_before_open)
    created = service.create_import()
    result = service.run_import(created["session_id"])
    copied = (
        workspace
        / "imports"
        / created["session_id"]
        / "source_copy"
        / "Department-A"
        / "invoice.txt"
    )

    assert result["state"] == "completed_with_errors"
    assert result["files_failed"] == 1
    assert not copied.exists()
    assert outside_file.read_bytes() == outside_original
    held_file = source / "Department-A-held" / "invoice.txt"
    assert held_file.read_text(encoding="utf-8") == "Synthetic source content"


def test_copy_and_hash_use_the_same_opened_source_file(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    source_file = source / "invoice.txt"
    source_file.write_text("Synthetic original content", encoding="utf-8")
    original = source_file.read_bytes()
    replacement = b"Synthetic replacement content"

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    original_open = service._open_source_file

    def replace_after_open(selected_source, path):
        handle = original_open(selected_source, path)
        path.rename(source / "held-original.txt")
        path.write_bytes(replacement)
        return handle

    monkeypatch.setattr(service, "_open_source_file", replace_after_open)
    created = service.create_import()
    result = service.run_import(created["session_id"])
    copied = workspace / "imports" / created["session_id"] / "source_copy" / "invoice.txt"
    manifest = service._read(service._json_path(created["session_id"], "manifest.json"))

    assert result["state"] == "completed"
    assert copied.read_bytes() == original
    assert (source / "held-original.txt").read_bytes() == original
    assert source_file.read_bytes() == replacement
    assert manifest["files"]["invoice.txt"]["sha256"] == sha256_file(copied)


@pytest.mark.parametrize(
    "reader", ["status", "list_sessions", "search", "inventory", "understanding"]
)
def test_session_state_readers_do_not_wait_for_metadata_lock(tmp_path, monkeypatch, reader):
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
        assert read_started.wait(timeout=1)
        assert read_finished.wait(timeout=1)
    finally:
        lock.release()

    thread.join(timeout=1)
    assert not thread.is_alive()
    assert not errors


def _configure_synthetic_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    return workspace, source


def test_status_polling_is_prompt_during_import_and_import_stays_verified(
    tmp_path, monkeypatch
):
    workspace, source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    source_file = source / "synthetic.txt"
    source_file.write_text("synthetic import payload", encoding="utf-8")
    original = source_file.read_bytes()
    service = SafeWorkspaceService()
    session = service.create_import()
    import_started = threading.Event()
    continue_import = threading.Event()
    status_returned = threading.Event()
    results = []
    errors = []
    original_open = service._open_source_file

    def blocked_open(source_root, path):
        import_started.set()
        if not continue_import.wait(timeout=5):
            raise TimeoutError("Test did not release the import worker.")
        return original_open(source_root, path)

    monkeypatch.setattr(service, "_open_source_file", blocked_open)

    def run_import():
        try:
            results.append(service.run_import(session["session_id"]))
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=run_import)
    worker.start()
    try:
        assert import_started.wait(timeout=2)

        def poll_status():
            try:
                results.append(service.status(session["session_id"]))
            except Exception as exc:
                errors.append(exc)
            finally:
                status_returned.set()

        poller = threading.Thread(target=poll_status)
        poller.start()
        assert status_returned.wait(timeout=1)
        poller.join(timeout=1)
        assert not poller.is_alive()
        polled = results.pop()
        assert polled["state"] == "running"
        assert 0 <= polled["progress"] < 1
    finally:
        continue_import.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert not errors
    completed = service.status(session["session_id"])
    copied = workspace / "imports" / session["session_id"] / "source_copy" / "synthetic.txt"
    manifest = service._read(service._json_path(session["session_id"], "manifest.json"))
    assert completed["state"] == "completed"
    assert completed["progress"] == 1
    assert completed["files_copied"] == completed["files_verified"] == 1
    assert copied.read_bytes() == original
    assert manifest["files"]["synthetic.txt"]["sha256"] == sha256_file(copied)
    assert source_file.read_bytes() == original


def test_status_polling_is_prompt_during_scan_and_scan_completes(
    tmp_path, monkeypatch
):
    _workspace, source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    (source / "synthetic.txt").write_text("synthetic scan payload", encoding="utf-8")
    service = SafeWorkspaceService()
    session = service.create_import()
    assert service.run_import(session["session_id"])["state"] == "completed"
    scan_started = threading.Event()
    continue_scan = threading.Event()
    status_returned = threading.Event()
    results = []
    errors = []
    original_files = service._files

    def blocked_files(root):
        for path in original_files(root):
            scan_started.set()
            if not continue_scan.wait(timeout=5):
                raise TimeoutError("Test did not release the scan worker.")
            yield path

    monkeypatch.setattr(service, "_files", blocked_files)

    def run_scan():
        try:
            results.append(service.scan(session["session_id"]))
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=run_scan)
    worker.start()
    try:
        assert scan_started.wait(timeout=2)

        def poll_status():
            try:
                results.append(service.status(session["session_id"]))
            except Exception as exc:
                errors.append(exc)
            finally:
                status_returned.set()

        poller = threading.Thread(target=poll_status)
        poller.start()
        assert status_returned.wait(timeout=1)
        poller.join(timeout=1)
        assert not poller.is_alive()
        polled = results.pop()
        assert polled["state"] == "scanning"
    finally:
        continue_scan.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert not errors
    final_status = service.status(session["session_id"])
    inventory = service.inventory(session["session_id"])
    assert final_status["state"] == "scanned"
    assert final_status["files_total"] == final_status["files_verified"] == 1
    assert inventory["total"] == 1


def test_concurrent_status_reads_observe_complete_atomic_json(tmp_path, monkeypatch):
    workspace, source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    for index in range(8):
        (source / f"synthetic-{index}.txt").write_text(
            f"synthetic payload {index}", encoding="utf-8"
        )
    service = SafeWorkspaceService()
    session = service.create_import()
    status_path = service._json_path(session["session_id"], "status.json")
    replacement_started = threading.Event()
    allow_replace = threading.Event()
    original_replace = os.replace
    paused = False
    read_errors = []
    results = []

    def pause_first_status_replace(source_path, destination_path):
        nonlocal paused
        if Path(destination_path) == status_path and not paused:
            paused = True
            replacement_started.set()
            if not allow_replace.wait(timeout=5):
                raise TimeoutError("Test did not release atomic status replacement.")
        return original_replace(source_path, destination_path)

    monkeypatch.setattr(
        "app.services.safe_workspace_service.os.replace", pause_first_status_replace
    )

    worker = threading.Thread(
        target=lambda: results.append(service.run_import(session["session_id"]))
    )
    worker.start()
    try:
        assert replacement_started.wait(timeout=2)
        start_readers = threading.Barrier(9)

        def read_status_repeatedly():
            try:
                start_readers.wait(timeout=2)
                for _ in range(20):
                    results.append(service.status(session["session_id"]))
            except Exception as exc:
                read_errors.append(exc)

        readers = [threading.Thread(target=read_status_repeatedly) for _ in range(8)]
        for reader in readers:
            reader.start()
        start_readers.wait(timeout=2)
        allow_replace.set()
        for reader in readers:
            reader.join(timeout=5)
            assert not reader.is_alive()
    finally:
        allow_replace.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert not read_errors
    assert all(isinstance(value, dict) and "state" in value for value in results)
    manifest = service._read(service._json_path(session["session_id"], "manifest.json"))
    copied_files = list(
        (workspace / "imports" / session["session_id"] / "source_copy").rglob("*")
    )
    assert len(manifest["files"]) == 8
    assert all(entry["verified"] for entry in manifest["files"].values())
    assert len([path for path in copied_files if path.is_file()]) == 8


def test_concurrent_import_and_scan_do_not_corrupt_session(tmp_path, monkeypatch):
    workspace, source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    source_file = source / "synthetic.txt"
    source_file.write_text("concurrent synthetic payload", encoding="utf-8")
    original = source_file.read_bytes()
    service = SafeWorkspaceService()
    session = service.create_import()
    import_started = threading.Event()
    continue_import = threading.Event()
    results = []
    original_open = service._open_source_file

    def blocked_open(source_root, path):
        import_started.set()
        if not continue_import.wait(timeout=5):
            raise TimeoutError("Test did not release the import worker.")
        return original_open(source_root, path)

    monkeypatch.setattr(service, "_open_source_file", blocked_open)
    worker = threading.Thread(
        target=lambda: results.append(service.run_import(session["session_id"]))
    )
    worker.start()
    try:
        assert import_started.wait(timeout=2)
        assert service.run_import(session["session_id"])["state"] == "running"
        with pytest.raises(ValueError, match="already running"):
            service.scan(session["session_id"])
    finally:
        continue_import.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    final_status = service.status(session["session_id"])
    copied = workspace / "imports" / session["session_id"] / "source_copy" / "synthetic.txt"
    manifest = service._read(service._json_path(session["session_id"], "manifest.json"))
    assert results[0]["state"] == final_status["state"] == "completed"
    assert copied.read_bytes() == original
    assert manifest["files"]["synthetic.txt"]["sha256"] == sha256_file(copied)
    assert source_file.read_bytes() == original


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
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
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
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", False)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    with pytest.raises(ValueError, match="ORIGINAL_READ_ONLY"):
        SafeWorkspaceService().validate_source(source)


def test_cross_process_session_operation_has_single_owner(tmp_path, monkeypatch):
    workspace, _source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    service = SafeWorkspaceService()
    session_id = service.create_import()["session_id"]
    context = multiprocessing.get_context("spawn")
    first_ready = context.Event()
    release_first = context.Event()
    first_result = context.Queue()
    second_ready = context.Event()
    second_release = context.Event()
    second_result = context.Queue()
    first = context.Process(
        target=_process_hold_operation,
        args=(str(workspace), session_id, first_ready, release_first, first_result),
    )
    second = context.Process(
        target=_process_hold_operation,
        args=(str(workspace), session_id, second_ready, second_release, second_result),
    )

    first.start()
    try:
        assert first_ready.wait(timeout=10)
        assert first_result.get(timeout=2) == "acquired"
        second.start()
        assert second_ready.wait(timeout=10)
        assert second_result.get(timeout=2) == "conflict"
    finally:
        release_first.set()
        if first.is_alive():
            first.join(timeout=10)
        if second.pid and second.is_alive():
            second.join(timeout=10)
    assert first.exitcode == 0
    assert second.exitcode == 0


def test_cross_process_status_updates_do_not_lose_fields(tmp_path, monkeypatch):
    workspace, _source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    service = SafeWorkspaceService()
    session_id = service.create_import()["session_id"]
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    result = context.Queue()
    processes = [
        context.Process(
            target=_process_update_status,
            args=(str(workspace), session_id, field, barrier, result),
        )
        for field in ("worker_one", "worker_two")
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert not process.is_alive()
        assert process.exitcode == 0
    assert [result.get(timeout=2) for _ in processes] == ["updated", "updated"]
    status = service.status(session_id)
    assert status["worker_one"] is True
    assert status["worker_two"] is True


def test_cross_process_reservation_recovers_after_process_exit(tmp_path, monkeypatch):
    workspace, _source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    service = SafeWorkspaceService()
    session_id = service.create_import()["session_id"]
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    process = context.Process(
        target=_process_exit_with_operation,
        args=(str(workspace), session_id, acquired),
    )
    process.start()
    assert acquired.wait(timeout=10)
    process.join(timeout=10)
    assert process.exitcode == 0

    with service._session_operation(session_id, "after-crash"):
        assert service.status(session_id)["state"] == "created"


def test_cross_process_operations_on_different_sessions_run_concurrently(
    tmp_path, monkeypatch
):
    workspace, _source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    service = SafeWorkspaceService()
    first_session = service.create_import()["session_id"]
    second_session = service.create_import()["session_id"]
    context = multiprocessing.get_context("spawn")
    first_ready = context.Event()
    release_first = context.Event()
    first_result = context.Queue()
    second_ready = context.Event()
    second_release = context.Event()
    second_result = context.Queue()
    first = context.Process(
        target=_process_hold_operation,
        args=(str(workspace), first_session, first_ready, release_first, first_result),
    )
    second = context.Process(
        target=_process_hold_operation,
        args=(str(workspace), second_session, second_ready, second_release, second_result),
    )

    first.start()
    try:
        assert first_ready.wait(timeout=10)
        assert first_result.get(timeout=2) == "acquired"
        second.start()
        assert second_ready.wait(timeout=10)
        assert second_result.get(timeout=2) == "acquired"
    finally:
        release_first.set()
        second_release.set()
        first.join(timeout=10)
        if second.pid:
            second.join(timeout=10)
    assert first.exitcode == 0
    assert second.exitcode == 0


def test_cross_process_atomic_json_replacement(tmp_path, monkeypatch):
    workspace, _source = _configure_synthetic_workspace(tmp_path, monkeypatch)
    service = SafeWorkspaceService()
    session_id = service.create_import()["session_id"]
    status_path = service._json_path(session_id, "status.json")
    service._write(status_path, {
        "marker": "A",
        "sequence": -1,
        "payload": "A" * 16384,
    })
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    result = context.Queue()
    process = context.Process(
        target=_process_write_status,
        args=(str(workspace), session_id, "B", barrier, result),
    )
    process.start()
    barrier.wait(timeout=10)
    snapshots = 0
    while process.is_alive():
        value = service._read(status_path)
        assert value["marker"] in {"A", "B"}
        assert len(value["payload"]) == 16384
        assert value["payload"] == value["marker"] * 16384
        snapshots += 1
    process.join(timeout=10)
    assert process.exitcode == 0
    assert result.get(timeout=2) == "written"
    final_value = service._read(status_path)
    assert final_value["marker"] in {"A", "B"}
    assert final_value["payload"] == final_value["marker"] * 16384
    assert snapshots > 0
