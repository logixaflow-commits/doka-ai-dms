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
    working_copy = imports / session_id / "source_copy"
    working_copy.mkdir(parents=True)
    (working_copy / "safe.txt").write_text("safe", encoding="utf-8")
    outside = workspace / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)

    digest = hashlib.sha256(b"safe").hexdigest()
    manifest = {
        "session_id": session_id,
        "source_root": str(tmp_path / "source"),
        "working_copy": str(working_copy),
        "files": {
            "safe.txt": {
                "relative_path": "safe.txt",
                "verified": True,
                "sha256": digest,
            }
        },
    }
    (tmp_path / "source").mkdir()
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
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".json").write_text(json.dumps({"sha256": digest}), encoding="utf-8")

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


def test_source_must_remain_read_only_in_personal_mode(monkeypatch):
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", False)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    with pytest.raises(ValueError, match="ORIGINAL_READ_ONLY"):
        settings._validate()
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)



def test_workspace_file_rejects_tampered_manifest_working_copy(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    session_id = "b" * 32
    session = workspace / "imports" / session_id
    session.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    manifest = {
        "session_id": session_id,
        "source_root": str(tmp_path),
        "working_copy": str(outside),
        "files": {"secret.txt": {
            "relative_path": "secret.txt",
            "verified": True,
            "sha256": hashlib.sha256(b"private").hexdigest(),
        }},
    }
    (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(Exception, match="manifest paths are invalid"):
        _safe_file(session_id, "secret.txt")



def test_workspace_rejects_symlinked_import_session_directory(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "imports").mkdir(parents=True)
    session_id = "e" * 32
    (workspace / "imports" / session_id).symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)

    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="cannot be a symlink"):
        service._dir(session_id)



def test_backup_restore_rejects_archives_over_entry_limit(tmp_path, monkeypatch):
    import importlib

    backup_module = importlib.import_module("app.services.workspace_backup_service")
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)
    (workspace / "one.txt").write_text("one", encoding="utf-8")

    service = WorkspaceBackupService()
    manifest = service.create()
    monkeypatch.setattr(backup_module, "_MAX_RESTORE_ENTRIES", 0)

    with pytest.raises(ValueError, match="too many entries"):
        service.restore_to_recovery(Path(manifest["archive"]).name)
    recovery_root = workspace / "Recovery"
    assert not list(recovery_root.glob("restore_*")) if recovery_root.exists() else True
