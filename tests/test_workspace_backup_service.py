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

    service = WorkspaceBackupService()
    try:
        service.restore_to_recovery(archive.name)
        assert False, "Expected unsafe archive rejection"
    except ValueError as exc:
        assert "unsafe path" in str(exc).lower()
    assert not (tmp_path / "escape.txt").exists()
