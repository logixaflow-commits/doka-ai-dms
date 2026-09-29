from pathlib import Path
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
