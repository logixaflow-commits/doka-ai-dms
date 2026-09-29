from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import require_staff
from app.services.safe_workspace_service import safe_workspace_service

router = APIRouter(prefix="/api/workspace", tags=["Workspace Files"], dependencies=[Depends(require_staff)])


def _safe_file(session_id: str, relative_path: str) -> Path:
    try:
        manifest = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "manifest.json")
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown import session.") from exc
    if not manifest:
        raise HTTPException(status_code=404, detail="Unknown import session.")
    root = Path(manifest["working_copy"]).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path is outside the working copy.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found in working copy.")
    return candidate


@router.get("/imports/{session_id}/files/{relative_path:path}")
async def download_working_copy_file(session_id: str, relative_path: str, download: bool = False):
    path = _safe_file(session_id, relative_path)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )
