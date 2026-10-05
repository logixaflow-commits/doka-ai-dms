from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cloudflare_worker_uses_bundle_safe_top_level_imports():
    worker_root = REPO_ROOT / "cloudflare_worker"
    entrypoint = (worker_root / "main.py").read_text(encoding="utf-8")
    runtime = (worker_root / "storage_runtime.py").read_text(encoding="utf-8")

    assert "from cloudflare_worker." not in entrypoint
    assert "from cloudflare_worker." not in runtime

    for module in ("storage_b2", "storage_cloudinary", "storage_google_drive", "storage_router", "storage_supabase"):
        assert module in runtime


def test_cloudflare_worker_entrypoint_and_runtime_are_present():
    assert (REPO_ROOT / "wrangler.jsonc").is_file()
    assert (REPO_ROOT / "cloudflare_worker" / "main.py").is_file()
    assert (REPO_ROOT / "cloudflare_worker" / "storage_runtime.py").is_file()
