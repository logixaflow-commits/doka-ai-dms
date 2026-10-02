"""Regression guard for the Cloudflare Worker safe-preview contract."""
from pathlib import Path


WORKER_SOURCE = (
    Path(__file__).resolve().parents[2] / "cloudflare_worker" / "main.py"
).read_text(encoding="utf-8")


def test_worker_preview_route_is_authenticated_and_owner_scoped():
    assert '@app.get("/api/documents/{document_id}/preview")' in WORKER_SOURCE
    assert 'user_id: str = Depends(require_user)' in WORKER_SOURCE
    assert '&owner_id=eq.{quote(user_id, safe=\'\')}&deleted_at=is.null&limit=1' in WORKER_SOURCE


def test_worker_preview_allows_only_passive_formats_and_audits():
    for content_type in (
        '"application/pdf"',
        '"image/jpeg"',
        '"image/png"',
        '"image/gif"',
        '"image/webp"',
        '"text/plain"',
        '"text/csv"',
    ):
        assert content_type in WORKER_SOURCE
    assert 'status_code=415, detail="Preview is not available for this file type."' in WORKER_SOURCE
    assert '_audit(request, user_id, "preview"' in WORKER_SOURCE
