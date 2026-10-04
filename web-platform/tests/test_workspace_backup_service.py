from pathlib import Path
import hashlib
import json
import zipfile

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
    session = workspace / "imports" / "0123456789abcdef0123456789abcdef"
    session.mkdir(parents=True)
    (session / ".operation.lock").write_bytes(b"\0")
    (session / ".metadata.lock").write_bytes(b"\0")
    (session / "status.json").write_text('{"state":"created"}', encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    manifest = WorkspaceBackupService().create()
    with zipfile.ZipFile(manifest["archive"]) as archive:
        names = archive.namelist()

    assert "imports/0123456789abcdef0123456789abcdef/status.json" in names
    assert not any(name.endswith((".operation.lock", ".metadata.lock")) for name in names)



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

    restored = service.restore_to_recovery(Path(manifest["archive"]).name)

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
        service.restore_to_recovery(archive.name)
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
        service.restore_to_recovery(archive.name)
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
        service.restore_to_recovery(Path(manifest["archive"]).name)
    assert not list(outside.iterdir())
