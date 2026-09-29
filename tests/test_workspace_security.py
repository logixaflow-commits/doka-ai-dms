from pathlib import Path
import zipfile

import pytest

from app.core.config import settings
from app.services.safe_workspace_service import SafeWorkspaceService
from app.services.workspace_backup_service import WorkspaceBackupService


def test_invalid_session_id_cannot_escape_imports(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="Invalid import session id"):
        service.status("..")


def test_backup_restore_rejects_zip_slip(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    archive = backups / "workspace_malicious.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escaped.txt", "must not extract")

    service = WorkspaceBackupService()
    with pytest.raises(ValueError, match="unsafe path"):
        service.restore_to_recovery(archive.name)
    assert not (workspace / "escaped.txt").exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_source_write_is_rejected_even_without_source_root(monkeypatch):
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", True)
    with pytest.raises(ValueError, match="ALLOW_SOURCE_WRITE"):
        settings._validate()
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
