from pathlib import Path
import hashlib
import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from app.core.config import settings
from app.services.workspace_backup_service import WorkspaceBackupService


def test_backup_create_and_verify(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    (workspace / "example.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    service = WorkspaceBackupService()
    manifest = service.create()
    assert Path(manifest["archive"]).is_file()

    verified = service.verify(Path(manifest["archive"]).name)
    assert verified["verified"] is True
    assert verified["sha256"] == manifest["sha256"]


def _write_retention_backup(root, number, created_at):
    archive = root / f"workspace_{number:03}.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("synthetic.txt", f"backup {number}")
    manifest = {
        "schema_version": 1,
        "created_at": created_at.isoformat(),
        "archive": str(archive),
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    archive.with_suffix(".json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return archive


def _configure_retention(tmp_path, monkeypatch, minimum=5):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)
    monkeypatch.setattr(settings, "BACKUP_RETENTION_DAYS", 30)
    monkeypatch.setattr(settings, "BACKUP_MINIMUM_RETAINED", minimum)
    return workspace, backups, WorkspaceBackupService()


@pytest.mark.parametrize(("count", "minimum", "expected_removed"), [
    (2, 5, 0),
    (5, 5, 0),
    (7, 5, 2),
])
def test_prune_retains_configured_minimum_and_newest(
    tmp_path, monkeypatch, count, minimum, expected_removed
):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum)
    oldest = datetime.now(timezone.utc) - timedelta(days=60)
    archives = [
        _write_retention_backup(backups, number, oldest + timedelta(minutes=number))
        for number in range(count)
    ]

    preview = service.prune(dry_run=True)

    assert preview["minimum_retained"] == minimum
    assert preview["dry_run"] is True
    assert len(preview["would_remove"]) == expected_removed
    assert preview["removed"] == []
    assert all(archive.exists() for archive in archives)
    expected_retained = [archive.name for archive in reversed(archives[-minimum:])]
    assert preview["retained"] == expected_retained

    result = service.prune(confirm=True)
    assert len(result["removed"]) == expected_removed
    assert len(list(backups.glob("workspace_*.zip"))) == count - expected_removed
    assert result["retained"] == expected_retained


def test_prune_fails_closed_on_incomplete_metadata(tmp_path, monkeypatch):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum=1)
    oldest = datetime.now(timezone.utc) - timedelta(days=60)
    archive = _write_retention_backup(backups, 1, oldest)
    _write_retention_backup(backups, 2, oldest + timedelta(minutes=1))
    manifest_path = archive.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["created_at"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete metadata"):
        service.prune(confirm=True)

    assert len(list(backups.glob("workspace_*.zip"))) == 2


def test_prune_fails_closed_on_manifest_path_traversal(tmp_path, monkeypatch):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum=1)
    archive = _write_retention_backup(
        backups, 1, datetime.now(timezone.utc) - timedelta(days=60)
    )
    manifest_path = archive.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["archive"] = "../outside.zip"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete metadata"):
        service.prune(confirm=True)
    assert archive.exists()


def test_prune_rejects_symlinked_backup_candidates(
    tmp_path, monkeypatch
):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum=1)
    outside = tmp_path / "outside.zip"
    _write_retention_backup(
        backups, 1, datetime.now(timezone.utc) - timedelta(days=60)
    )
    with zipfile.ZipFile(outside, "w") as bundle:
        bundle.writestr("synthetic.txt", "outside")
    if sys.platform == "win32":
        pytest.skip("Symlink escape protection is exercised on Linux CI.")
    (backups / "workspace_999.zip").symlink_to(outside)

    with pytest.raises(ValueError, match="symlinked"):
        service.prune(confirm=True)
    assert outside.exists()


def test_prune_recalculates_after_preview(tmp_path, monkeypatch):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum=1)
    old = datetime.now(timezone.utc) - timedelta(days=60)
    candidate = _write_retention_backup(backups, 1, old)
    other = _write_retention_backup(backups, 2, old + timedelta(minutes=1))

    preview = service.prune(dry_run=True)
    assert preview["would_remove"] == [candidate.name]

    metadata_path = candidate.with_suffix(".json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["created_at"] = datetime.now(timezone.utc).isoformat()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    result = service.prune(confirm=True)

    assert result["removed"] == [other.name]
    assert candidate.exists()


def test_concurrent_prunes_are_serialized(tmp_path, monkeypatch):
    _, backups, service = _configure_retention(tmp_path, monkeypatch, minimum=1)
    old = datetime.now(timezone.utc) - timedelta(days=60)
    _write_retention_backup(backups, 1, old)
    _write_retention_backup(backups, 2, old + timedelta(minutes=1))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.prune(confirm=True), range(2)))

    assert sorted(len(result["removed"]) for result in results) == [0, 1]
    assert len(list(backups.glob("workspace_*.zip"))) == 1


def test_restore_requires_explicit_confirmation(tmp_path, monkeypatch):
    _, _, service = _configure_retention(tmp_path, monkeypatch)
    manifest = service.create()

    with pytest.raises(ValueError, match="explicit confirmation"):
        service.restore_to_recovery(Path(manifest["archive"]).name)

    with pytest.raises(ValueError, match="explicit confirmation"):
        service.prune()


def test_backup_excludes_recovery_artifacts(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    recovery = workspace / "Recovery" / "restore_old"
    workspace.mkdir()
    recovery.mkdir(parents=True)
    (workspace / "active.txt").write_text("active", encoding="utf-8")
    (recovery / "derived.txt").write_text("derived", encoding="utf-8")

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    service = WorkspaceBackupService()
    manifest = service.create()
    with zipfile.ZipFile(manifest["archive"]) as archive:
        names = archive.namelist()

    assert "active.txt" in names
    assert not any(name.startswith("Recovery/") for name in names)


def test_backup_excludes_session_coordination_locks(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    session_id = "0123456789abcdef0123456789abcdef"
    session = workspace / "imports" / "0123456789abcdef0123456789abcdef"
    session.mkdir(parents=True)
    (session / ".operation.lock").write_bytes(b"\0")
    (session / ".metadata.lock").write_bytes(b"\0")
    (session / "status.json").write_text('{"state":"created"}', encoding="utf-8")
    nested = session / "source_copy" / "Department-A"
    nested.mkdir(parents=True)
    nested_operation_lock = nested / ".operation.lock"
    nested_metadata_lock = nested / ".metadata.lock"
    nested_operation_lock.write_text("synthetic user document", encoding="utf-8")
    nested_metadata_lock.write_text("synthetic user metadata", encoding="utf-8")
    outside_imports = workspace / ".operation.lock"
    outside_imports.write_text("synthetic workspace document", encoding="utf-8")
    imports_root_lock = workspace / "imports" / ".metadata.lock"
    imports_root_lock.write_text("synthetic imports document", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    manifest = WorkspaceBackupService().create()
    with zipfile.ZipFile(manifest["archive"]) as archive:
        names = archive.namelist()

    assert f"imports/{session_id}/status.json" in names
    assert f"imports/{session_id}/source_copy/Department-A/.operation.lock" in names
    assert f"imports/{session_id}/source_copy/Department-A/.metadata.lock" in names
    assert ".operation.lock" in names
    assert "imports/.metadata.lock" in names
    assert f"imports/{session_id}/.operation.lock" not in names
    assert f"imports/{session_id}/.metadata.lock" not in names



def test_restore_to_recovery_does_not_change_active_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    (workspace / "active.txt").write_text("active-before", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    service = WorkspaceBackupService()
    manifest = service.create()
    (workspace / "active.txt").write_text("active-after", encoding="utf-8")
    before = (workspace / "active.txt").read_bytes()

    restored = service.restore_to_recovery(Path(manifest["archive"]).name, confirm=True)

    assert (workspace / "active.txt").read_bytes() == before
    assert restored["active_workspace_changed"] is False
    recovery_file = Path(restored["recovery_path"]) / "active.txt"
    assert recovery_file.read_text(encoding="utf-8") == "active-before"


def test_restore_rejects_zip_path_traversal(tmp_path, monkeypatch):
    import zipfile
    from app.core.config import settings
    from app.services.workspace_backup_service import WorkspaceBackupService

    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    archive = backups / "malicious.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "must not escape")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".json").write_text(json.dumps({"sha256": digest}), encoding="utf-8")

    service = WorkspaceBackupService()
    try:
        service.restore_to_recovery(archive.name, confirm=True)
        assert False, "Expected unsafe archive rejection"
    except ValueError as exc:
        assert "unsafe path" in str(exc).lower()
    assert not (tmp_path / "escape.txt").exists()


def test_restore_rejects_modified_archive_before_extracting(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    service = WorkspaceBackupService()
    manifest = service.create()
    archive = Path(manifest["archive"])
    with archive.open("ab") as handle:
        handle.write(b"tampered")

    import pytest
    with pytest.raises(ValueError, match="integrity verification failed"):
        service.restore_to_recovery(archive.name, confirm=True)
    recovery = workspace / "Recovery"
    assert not recovery.exists() or not list(recovery.iterdir())


def test_verify_rejects_archive_without_manifest(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    archive = backups / "workspace_orphan.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("data.txt", "data")

    import pytest
    service = WorkspaceBackupService()
    with pytest.raises(ValueError, match="manifest is missing"):
        service.verify(archive.name)


def test_backup_excludes_symlinked_files(tmp_path, monkeypatch, make_symlink):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("must not be backed up", encoding="utf-8")
    (workspace / "inside.txt").write_text("safe", encoding="utf-8")
    make_symlink(workspace / "linked-secret.txt", outside)

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)
    service = WorkspaceBackupService()
    manifest = service.create()
    with zipfile.ZipFile(manifest["archive"]) as zf:
        names = zf.namelist()
    assert "inside.txt" in names
    assert "linked-secret.txt" not in names



def test_restore_rejects_symlinked_recovery_directory(
    tmp_path, monkeypatch, make_symlink
):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    service = WorkspaceBackupService()
    manifest = service.create()
    make_symlink(workspace / "Recovery", outside, target_is_directory=True)

    import pytest
    with pytest.raises(ValueError, match="Recovery directory cannot be a symlink"):
        service.restore_to_recovery(Path(manifest["archive"]).name, confirm=True)
    assert not list(outside.iterdir())
