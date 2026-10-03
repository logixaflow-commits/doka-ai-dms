from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.safe_workspace_service import safe_workspace_service
from app.services.workspace_backup_service import workspace_backup_service
from app.services.ocr_validation_service import ocr_validation_service
from app.core.supabase_auth import require_local_workspace_user

router = APIRouter(prefix="/api/workspace", tags=["Safe Workspace"], dependencies=[Depends(require_local_workspace_user)])


class OrganizationApplyRequest(BaseModel):
    approved_paths: list[str] = Field(default_factory=list, min_length=1)
    confirm: bool = Field(default=False, description="Must be true to copy approved files into Final.")


class ImportRequest(BaseModel):
    source: Optional[str] = Field(default=None, description="Local source folder; defaults to SOURCE_ROOT.")


@router.get("/imports")
async def list_imports(limit: int = 50):
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=400, detail="Invalid limit.")
    return {"imports": safe_workspace_service.list_sessions(limit)}

@router.post("/imports")
async def create_import(request: ImportRequest, background_tasks: BackgroundTasks):
    try:
        status = safe_workspace_service.create_import(request.source)
        background_tasks.add_task(safe_workspace_service.run_import, status["session_id"])
        return {"message": "Import started. Source is read-only; work happens on a verified copy.", **status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ocr/validate")
async def validate_ocr():
    return ocr_validation_service.validate()


@router.post("/backups")
async def create_backup():
    try:
        return workspace_backup_service.create()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backup failed: {exc}") from exc


@router.get("/backups")
async def list_backups():
    return {"backups": workspace_backup_service.list_backups()}


@router.post("/backups/verify")
async def verify_backup(archive_name: str):
    try:
        return workspace_backup_service.verify(archive_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backups/restore")
async def restore_backup(archive_name: str):
    try:
        return workspace_backup_service.restore_to_recovery(archive_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backups/prune")
async def prune_backups():
    return workspace_backup_service.prune()


@router.post("/imports/{session_id}/resume")
async def resume_import(session_id: str, background_tasks: BackgroundTasks):
    try:
        status = safe_workspace_service.status(session_id)
        background_tasks.add_task(safe_workspace_service.run_import, session_id)
        return {"message": "Import resumed.", **status}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/imports/{session_id}/understand")
async def understand_import(session_id: str):
    try:
        from app.services.document_understanding_service import document_understanding_service
        return document_understanding_service.analyze(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/imports/{session_id}/plan")
async def organization_plan(session_id: str):
    try:
        from app.services.organization_planner import organization_planner
        return organization_planner.plan(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/imports/{session_id}/apply")
async def apply_organization(session_id: str, request: OrganizationApplyRequest):
    if request.confirm is not True:
        raise HTTPException(status_code=400, detail="Explicit confirm=true is required.")
    try:
        from app.services.organization_planner import organization_planner
        return organization_planner.apply(session_id, request.approved_paths)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class OCRCorrectionRequest(BaseModel):
    text: str = Field(default="", max_length=1000000)


@router.get("/imports/{session_id}/understanding")
async def get_understanding(session_id: str):
    try:
        session = safe_workspace_service._dir(session_id)
        value = safe_workspace_service._read(session / "understanding.json")
        if not value:
            raise ValueError("Understanding is not available. Run Read / OCR first.")
        corrections = safe_workspace_service._read(session / "ocr_corrections.json")
        for item in value.get("results", []):
            rel = item.get("relative_path")
            if rel in corrections.get("results", {}):
                item["corrected_text"] = corrections["results"][rel]
                item["ocr_corrected"] = True
        return value
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/imports/{session_id}/understanding/{relative_path:path}")
async def save_ocr_correction(session_id: str, relative_path: str, request: OCRCorrectionRequest):
    try:
        manifest = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "manifest.json")
        )
        if not manifest:
            raise ValueError("Unknown import session.")
        if relative_path not in manifest.get("files", {}):
            raise ValueError("File is not a verified import-manifest entry.")
        if manifest["files"][relative_path].get("verified") is not True:
            raise ValueError("Only verified imported files can receive OCR corrections.")

        session = safe_workspace_service._dir(session_id)
        corrections_path = session / "ocr_corrections.json"
        corrections = safe_workspace_service._read(corrections_path)
        corrections.setdefault("schema_version", 1)
        corrections.setdefault("session_id", session_id)
        corrections.setdefault("results", {})
        if request.text.strip():
            corrections["results"][relative_path] = request.text
        else:
            corrections["results"].pop(relative_path, None)
        corrections["updated_at"] = safe_workspace_service.utc_now()
        safe_workspace_service._write(corrections_path, corrections)
        return {
            "session_id": session_id,
            "relative_path": relative_path,
            "saved": bool(request.text.strip()),
            "message": "OCR correction saved as metadata; source and working document are unchanged.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/imports/{session_id}/undo")
async def undo_organization(session_id: str):
    try:
        from app.services.organization_planner import organization_planner
        return organization_planner.undo(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/imports/{session_id}/scan")
async def scan_import(session_id: str):
    try:
        return safe_workspace_service.scan(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/imports/{session_id}")
async def import_status(session_id: str):
    try:
        return safe_workspace_service.status(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/imports/{session_id}/search")
async def search_import(
    session_id: str,
    q: str = "",
    limit: int = 100,
    extension: str | None = None,
    category: str | None = None,
    review_only: bool = False,
):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="Invalid limit.")
    try:
        return safe_workspace_service.search(
            session_id,
            q,
            limit,
            extension=extension,
            category=category,
            review_only=review_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/imports/{session_id}/inventory")
async def import_inventory(session_id: str, limit: int = 500, offset: int = 0):
    if not 1 <= limit <= 5000 or offset < 0:
        raise HTTPException(status_code=400, detail="Invalid limit/offset.")
    try:
        return safe_workspace_service.inventory(session_id, limit, offset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
