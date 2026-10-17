from pathlib import Path


WEB_PLATFORM = Path(__file__).resolve().parents[1]
WORKER = (WEB_PLATFORM / "backend" / "cloudflare_worker" / "main.py").read_text(encoding="utf-8")
PRODUCTION_CONFIG = (WEB_PLATFORM.parents[1] / "wrangler.jsonc").read_text(encoding="utf-8")
STAGING_CONFIG = (WEB_PLATFORM.parents[1] / "wrangler.staging.jsonc").read_text(encoding="utf-8")


def test_cors_policy_reads_request_scoped_worker_bindings():
    assert "def _worker_config_value(name: str, scope: dict | None = None)" in WORKER
    assert 'bindings = scope.get("env")' in WORKER
    assert "allow_origins=_cors_origins(scope)" in WORKER
    assert "allow_origin_regex=_cors_origin_regex(scope)" in WORKER
    assert "app.add_middleware(WorkerAwareCORSMiddleware)" in WORKER


def test_preview_origin_regex_is_opt_in_and_staging_only():
    assert 'DOKA_CORS_ALLOW_PREVIEW_ORIGINS": "true"' in STAGING_CONFIG
    assert "DOKA_CORS_ALLOW_PREVIEW_ORIGINS" not in PRODUCTION_CONFIG
    assert 'if enabled == "true"' in WORKER
    assert r"^https://enterprise-ai-dms-git-[a-z0-9-]+-logixaflow-9859\.vercel\.app$" in WORKER


def test_staging_config_uses_only_staging_supabase_and_d1():
    assert "gzxybtqquzycogaowdbj.supabase.co" in STAGING_CONFIG
    assert "11baa497-e6f7-4054-8e9f-3a21baec93f3" in STAGING_CONFIG
    assert "jkobgssaqifzrqfirdfu.supabase.co" not in STAGING_CONFIG
    assert "4f3a294b-11ae-4ba7-903b-6f32539cebce" not in STAGING_CONFIG
