from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.supabase_auth import require_authenticated_user
from app.services.safe_workspace_service import safe_workspace_service, sha256_file

router = APIRouter(
    prefix="/api/workspace",
    tags=["Workspace Files"],
    dependencies=[Depends(require_authenticated_user)],
)


def _safe_file(session_id: str, relative_path: str) -> tuple[Path, dict]:
    try:
        manifest = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "manifest.json")
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown import session.") from exc
    if not manifest:
        raise HTTPException(status_code=404, detail="Unknown import session.")

    try:
        _source, root = safe_workspace_service.validate_manifest_paths(session_id, manifest)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Import manifest paths are invalid.") from exc
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="Working copy is unavailable.")

    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path is outside the working copy.") from exc

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found in working copy.")

    normalized = candidate.relative_to(root).as_posix()
    entry = manifest.get("files", {}).get(normalized)
    if not entry or entry.get("verified") is not True:
        raise HTTPException(status_code=409, detail="File is not a verified import-manifest entry.")

    expected_hash = str(entry.get("sha256", "")).lower()
    if len(expected_hash) != 64:
        raise HTTPException(status_code=409, detail="File manifest hash is missing or invalid.")

    try:
        actual_hash = sha256_file(candidate)
    except OSError as exc:
        raise HTTPException(status_code=404, detail="File is no longer readable.") from exc

    if actual_hash.lower() != expected_hash:
        raise HTTPException(
            status_code=409,
            detail="File integrity check failed; the working copy changed after import.",
        )

    return candidate, entry


@router.get("/imports/{session_id}/files/{relative_path:path}")
async def download_working_copy_file(
    session_id: str,
    relative_path: str,
    download: bool = False,
):
    path, _entry = _safe_file(session_id, relative_path)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )
