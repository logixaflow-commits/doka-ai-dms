from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from app.services.metadata_extractor import metadata_extractor
from app.services.safe_workspace_service import SafeWorkspaceService


TEXT_EXTENSIONS = {
    ".txt", ".csv", ".tsv", ".json", ".xml", ".md", ".log", ".yaml", ".yml",
    ".html", ".htm", ".py", ".js", ".ts", ".tsx", ".jsx", ".sql",
}


class DocumentUnderstandingService:
    """Local-only content extraction and metadata enrichment. AI is not used here."""

    def __init__(self, workspace: SafeWorkspaceService):
        self.workspace = workspace

    def _extract_text(self, path: Path) -> tuple[str, str]:
        ext = path.suffix.lower()
        if ext in TEXT_EXTENSIONS:
            for encoding in ("utf-8", "utf-16", "cp1252"):
                try:
                    return path.read_text(encoding=encoding, errors="strict"), "text"
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return "", "text_unreadable"

        if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            try:
                from app.services.ocr_service import ocr_service
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                text, language = ocr_service.process_file(str(path), mime)
                return text or "", language or "unknown"
            except Exception as exc:
                logger.warning("OCR failed for %s: %s", path, exc)
                return "", "ocr_failed"

        return "", "not_text_extracted"

    def analyze(self, session_id: str) -> Dict[str, Any]:
        session = self.workspace._dir(session_id)
        manifest = self.workspace._read(session / "manifest.json")
        if not manifest:
            raise ValueError(f"Unknown import session: {session_id}")

        root = Path(manifest["working_copy"]).resolve()
        if not root.is_dir():
            raise ValueError("Working copy does not exist.")

        results = []
        for item in manifest.get("files", {}).values():
            if not item.get("verified"):
                continue
            path = Path(item["working_path"])
            if not path.exists():
                continue
            text, method = self._extract_text(path)
            metadata: Dict[str, Any] = {}
            if text.strip():
                try:
                    metadata = metadata_extractor.extract(text)
                except Exception as exc:
                    logger.warning("Metadata extraction failed for %s: %s", path, exc)
            results.append({
                "relative_path": item["relative_path"],
                "filename": item["filename"],
                "extension": item["extension"],
                "sha256": item["sha256"],
                "extraction_method": method,
                "text_length": len(text),
                "language": method if method in {"mya", "eng", "mya+eng"} else None,
                "metadata": metadata,
                "text_preview": text[:2000],
            })

        result = {
            "schema_version": 1,
            "session_id": session_id,
            "analyzed_files": len(results),
            "analyzed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "ai_used": False,
            "results": results,
        }
        self.workspace._write(session / "understanding.json", result)
        return {k: v for k, v in result.items() if k != "results"}


document_understanding_service = DocumentUnderstandingService(SafeWorkspaceService())
