import pytest

from app.core.config import settings
from app.services.workspace_backup_service import WorkspaceBackupService


def configure_roots(monkeypatch, tmp_path, backup_root):
    working_root = tmp_path / "workspace"
    source_root = tmp_path / "source"
    monkeypatch.setattr(settings, "WORKING_ROOT", working_root)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backup_root)
    return working_root, source_root


@pytest.mark.parametrize("location", ["inside_workspace", "workspace_parent", "inside_source", "source_parent"])
def test_backup_root_rejects_overlap_with_protected_roots(monkeypatch, tmp_path, location):
    working_root = tmp_path / "workspace"
    source_root = tmp_path / "source"
    candidates = {
        "inside_workspace": working_root / "Backups",
        "workspace_parent": tmp_path,
        "inside_source": source_root / "Backups",
        "source_parent": tmp_path,
    }
    backup_root = candidates[location]
    configure_roots(monkeypatch, tmp_path, backup_root)

    with pytest.raises(ValueError, match="must not overlap"):
        WorkspaceBackupService()._backup_root()


def test_backup_root_creates_safe_external_directory(monkeypatch, tmp_path):
    backup_root = tmp_path / "external-backups"
    configure_roots(monkeypatch, tmp_path, backup_root)

    result = WorkspaceBackupService()._backup_root()

    assert result == backup_root.resolve()
    assert result.is_dir()


def test_backup_root_rejects_symlink(monkeypatch, tmp_path, make_symlink):
    real_root = tmp_path / "real-backups"
    real_root.mkdir()
    link = tmp_path / "backup-link"
    make_symlink(link, real_root, target_is_directory=True)
    configure_roots(monkeypatch, tmp_path, link)

    with pytest.raises(ValueError, match="cannot be a symlink"):
        WorkspaceBackupService()._backup_root()


def _write_test_archive(backup_root, archive_name, members):
    import hashlib
    import json
    import zipfile

    archive = backup_root / archive_name
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, data in members:
            bundle.writestr(name, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".json").write_text(
        json.dumps({"sha256": digest}), encoding="utf-8"
    )
    return archive


def test_restore_rejects_case_colliding_paths_on_windows_filesystems(monkeypatch, tmp_path):
    backup_root = tmp_path / "backups"
    configure_roots(monkeypatch, tmp_path, backup_root)
    service = WorkspaceBackupService()
    service._backup_root()
    archive = _write_test_archive(
        backup_root,
        "workspace_case_collision.zip",
        [("Folder/Report.txt", b"one"), ("folder/report.txt", b"two")],
    )

    with pytest.raises(ValueError, match="case-colliding"):
        service.restore_to_recovery(archive.name)


def test_restore_rejects_windows_reserved_device_names(monkeypatch, tmp_path):
    backup_root = tmp_path / "backups"
    configure_roots(monkeypatch, tmp_path, backup_root)
    service = WorkspaceBackupService()
    service._backup_root()
    archive = _write_test_archive(
        backup_root,
        "workspace_reserved_name.zip",
        [("CON.txt", b"device name")],
    )

    with pytest.raises(ValueError, match="unsafe path"):
        service.restore_to_recovery(archive.name)
