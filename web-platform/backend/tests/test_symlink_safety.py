import os
import sys
from pathlib import Path

import pytest

from app.core.file_safety import safe_read


pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="symlink requires Linux"
)


def test_symlink_escape_denied(tmp_path, monkeypatch):
    allowed_root = tmp_path / "allowed"
    outside_root = tmp_path / "outside"
    allowed_root.mkdir()
    outside_root.mkdir()
    outside_file = outside_root / "secret.txt"
    outside_file.write_text("outside data", encoding="utf-8")
    link = allowed_root / "escape.txt"
    os.symlink(outside_file, link)
    monkeypatch.setenv("FILE_ROOT", str(allowed_root))

    with pytest.raises(PermissionError):
        safe_read(link)


def test_symlink_replacement_denied(tmp_path, monkeypatch):
    allowed_root = tmp_path / "allowed"
    outside_root = tmp_path / "outside"
    allowed_root.mkdir()
    outside_root.mkdir()
    target = allowed_root / "safe.txt"
    target.write_text("inside data", encoding="utf-8")
    outside_file = outside_root / "secret.txt"
    outside_file.write_text("outside data", encoding="utf-8")
    link = allowed_root / "requested.txt"
    os.symlink(target, link)
    monkeypatch.setenv("FILE_ROOT", str(allowed_root))

    original_resolve = Path.resolve
    replaced = False

    def resolve_with_replacement(path, *args, **kwargs):
        nonlocal replaced
        resolved = original_resolve(path, *args, **kwargs)
        if path == link and not replaced:
            link.unlink()
            os.symlink(outside_file, link)
            replaced = True
        return resolved

    monkeypatch.setattr(Path, "resolve", resolve_with_replacement)

    with pytest.raises(PermissionError):
        safe_read(link)


def test_normal_read_allowed(tmp_path, monkeypatch):
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    file_path = allowed_root / "message.txt"
    file_path.write_text("safe content", encoding="utf-8")
    monkeypatch.setenv("FILE_ROOT", str(allowed_root))

    assert safe_read(file_path) == "safe content"
