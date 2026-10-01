from pathlib import Path
import hashlib
import json
import zipfile

import pytest

from app.api.routes.workspace_files import _safe_file
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


def test_workspace_file_preview_rejects_path_escape_and_tampering(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    imports = workspace / "imports"
    session_id = "a" * 32
    working_copy = imports / session_id / "working_copy"
    working_copy.mkdir(parents=True)
    (working_copy / "safe.txt").write_text("safe", encoding="utf-8")
    outside = workspace / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)

    digest = hashlib.sha256(b"safe").hexdigest()
    manifest = {
        "working_copy": str(working_copy),
        "files": {
            "safe.txt": {
                "relative_path": "safe.txt",
                "verified": True,
                "sha256": digest,
            }
        },
    }
    (imports / session_id / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    path, entry = _safe_file(session_id, "safe.txt")
    assert path == (working_copy / "safe.txt").resolve()
    assert entry["verified"] is True

    with pytest.raises(Exception, match="outside the working copy"):
        _safe_file(session_id, "../outside.txt")

    (working_copy / "safe.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(Exception, match="integrity check failed"):
        _safe_file(session_id, "safe.txt")


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


def test_backup_verify_detects_modified_archive(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)

    (workspace / "state.json").write_text("original", encoding="utf-8")
    service = WorkspaceBackupService()
    manifest = service.create()
    assert service.verify(Path(manifest["archive"]).name)["verified"] is True

    with Path(manifest["archive"]).open("ab") as handle:
        handle.write(b"tampered")
    result = service.verify(Path(manifest["archive"]).name)
    assert result["verified"] is False


def test_source_write_is_rejected_even_without_source_root(monkeypatch):
    monkeypatch.setattr(settings, "SOURCE_ROOT", None)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", True)
    with pytest.raises(ValueError, match="ALLOW_SOURCE_WRITE"):
        settings._validate()
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
