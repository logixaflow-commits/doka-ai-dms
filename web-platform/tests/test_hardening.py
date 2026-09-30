from pathlib import Path


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
