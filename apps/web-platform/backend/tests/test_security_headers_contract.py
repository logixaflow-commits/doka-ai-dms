from pathlib import Path
WORKER=(Path(__file__).resolve().parents[1]/'cloudflare_worker'/'main.py').read_text(encoding='utf-8')
def test_security_headers_and_report_only_csp():
    for h in ('Strict-Transport-Security','X-Content-Type-Options','X-Frame-Options','Referrer-Policy','Permissions-Policy','Content-Security-Policy-Report-Only'): assert h in WORKER
    assert "script-src 'self'" in WORKER and "style-src 'self'" in WORKER and 'unsafe-inline' not in WORKER
    assert 'geolocation=(), camera=(), microphone=()' in WORKER
def test_csp_report_handler_is_bounded():
    assert '@app.post("/api/security/csp-report")' in WORKER and 'len(raw) > 16 * 1024' in WORKER
