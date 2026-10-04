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
