import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.workspace_backup_service import WorkspaceBackupService


def _configure(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    backup_root = tmp_path / "backups"
    workspace.mkdir()
    backup_root.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    return workspace, backup_root


def _write_archive(backup_root: Path, name: str, member_name: str, payload: bytes):
    archive = backup_root / name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, payload)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (backup_root / archive.with_suffix(".json").name).write_text(
        json.dumps({
            "schema_version": 1,
            "created_at": "2026-10-07T00:00:00+00:00",
            "source": "synthetic",
            "archive": str(archive),
            "sha256": digest,
            "session_id": None,
        }),
        encoding="utf-8",
    )
    return archive


def test_restore_rejects_zip_path_traversal(monkeypatch, tmp_path):
    workspace, backup_root = _configure(monkeypatch, tmp_path)
    archive = _write_archive(backup_root, "workspace_bad.zip", "../escaped.txt", b"sentinel")
    service = WorkspaceBackupService()

    with pytest.raises(ValueError, match="unsafe path"):
        service.restore_to_recovery(archive.name, confirm=True)

    assert not (workspace.parent / "escaped.txt").exists()
    assert not (workspace / "Recovery").exists()


def test_restore_creates_isolated_verified_recovery_tree(monkeypatch, tmp_path):
    workspace, backup_root = _configure(monkeypatch, tmp_path)
    archive = _write_archive(backup_root, "workspace_good.zip", "folder/file.txt", b"verified")
    service = WorkspaceBackupService()

    result = service.restore_to_recovery(archive.name, confirm=True)

    recovery = Path(result["recovery_path"])
    assert result["active_workspace_changed"] is False
    assert recovery.is_relative_to(workspace / "Recovery")
    assert (recovery / "folder" / "file.txt").read_bytes() == b"verified"
    assert service.verify(archive.name)["verified"] is True
