from pathlib import Path

import pytest

from app.core.config import settings


def test_personal_local_runtime_files_exist():
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "web-platform" / "backend" / "app" / "main.py").is_file()
    assert (repo_root / "web-platform" / "frontend" / "src" / "App.tsx").is_file()


def test_personal_local_safety_defaults_are_present_in_template():
    repo_root = Path(__file__).resolve().parents[2]
    env = (repo_root / "web-platform" / "backend" / ".env.example").read_text(encoding="utf-8")
    assert "ORIGINAL_READ_ONLY=true" in env
    assert "ALLOW_SOURCE_WRITE=false" in env
    assert "AI_ENABLED=false" in env
    assert "BOOTSTRAP_ADMIN_PASSWORD=" in env


def test_personal_local_rejects_writable_roots_outside_workspace(tmp_path: Path, monkeypatch):
    working = tmp_path / "workspace"
    working.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", working)
    monkeypatch.setattr(settings, "SOURCE_ROOT", tmp_path / "source")
    monkeypatch.setattr(settings, "BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr(settings, "FINAL_ROOT", tmp_path / "unsafe-final")
    monkeypatch.setattr(settings, "QUARANTINE_ROOT", working / "Quarantine")

    with pytest.raises(ValueError, match="FINAL_ROOT"):
        settings._validate()


def test_personal_local_rejects_backup_inside_workspace(tmp_path: Path, monkeypatch):
    working = tmp_path / "workspace"
    working.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", working)
    monkeypatch.setattr(settings, "SOURCE_ROOT", tmp_path / "source")
    monkeypatch.setattr(settings, "BACKUP_ROOT", working / "Backups")
    monkeypatch.setattr(settings, "FINAL_ROOT", working / "Final")
    monkeypatch.setattr(settings, "QUARANTINE_ROOT", working / "Quarantine")

    with pytest.raises(ValueError, match="BACKUP_ROOT"):
        settings._validate()
