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
    service = SafeWorkspaceService()
    with pytest.raises(ValueError, match="overlap"):
        service.validate_source(source)


def test_source_outside_workspace_is_allowed(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    service = SafeWorkspaceService()
    assert service.validate_source(source) == source.resolve()
