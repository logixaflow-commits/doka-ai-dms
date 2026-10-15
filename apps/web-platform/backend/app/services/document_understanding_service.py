from __future__ import annotations

import gc
import json
import mimetypes
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from app.services.metadata_extractor import metadata_extractor
from app.services.safe_workspace_service import SafeWorkspaceService, safe_workspace_service, sha256_file


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

        if ext == ".docx":
            try:
                with zipfile.ZipFile(path) as archive:
                    xml = archive.read("word/document.xml")
                root = ET.fromstring(xml)
                text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
                return re.sub(r"\s+", " ", text).strip(), "docx"
            except Exception as exc:
                logger.warning("DOCX extraction failed for %s: %s", path, exc)
                return "", "docx_failed"

        if ext in {".xlsx", ".xlsm"}:
            try:
                from openpyxl import load_workbook
                workbook = load_workbook(path, read_only=True, data_only=True)
                chunks = []
                for sheet in workbook.worksheets:
                    chunks.append(f"[Sheet: {sheet.title}]")
                    for row in sheet.iter_rows(values_only=True):
                        values = [str(value) for value in row if value is not None]
                        if values:
                            chunks.append(" | ".join(values))
                workbook.close()
                return "\n".join(chunks), "xlsx"
            except Exception as exc:
                logger.warning("Excel extraction failed for %s: %s", path, exc)
                return "", "xlsx_failed"

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
        with self.workspace._session_operation(session_id, "understanding"):
            return self._analyze_locked(session_id)

    def _analyze_locked(self, session_id: str) -> Dict[str, Any]:
        session = self.workspace._dir(session_id)
        manifest = self.workspace._read(session / "manifest.json")
        if not manifest:
            raise ValueError(f"Unknown import session: {session_id}")

        _source, root = self.workspace.validate_manifest_paths(session_id, manifest)
        if not root.is_dir():
            raise ValueError("Working copy does not exist.")

        # Resumability: load any existing/partial analysis results
        existing_results_map: Dict[str, Dict[str, Any]] = {}
        understanding_path = session / "understanding.json"
        if understanding_path.exists():
            try:
                existing_data = self.workspace._read(understanding_path)
                if isinstance(existing_data, dict):
                    for prev in existing_data.get("results", []):
                        if isinstance(prev, dict) and prev.get("relative_path"):
                            existing_results_map[prev["relative_path"]] = prev
            except Exception as exc:
                logger.warning("Could not read previous understanding.json for resume: %s", exc)

        # Hash-based deduplication cache across already analyzed files
        sha256_cache: Dict[str, Dict[str, Any]] = {}
        for prev in existing_results_map.values():
            if prev.get("sha256"):
                sha256_cache[prev["sha256"]] = prev

        results = []
        batch_counter = 0
        BATCH_FLUSH_INTERVAL = 50

        for relative_path, item in manifest.get("files", {}).items():
            if not item.get("verified"):
                continue
            if item.get("relative_path") != relative_path:
                raise ValueError("Import manifest contains an inconsistent relative path.")
            path = (root / Path(relative_path)).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError("Import manifest file path is outside the working copy.") from exc
            if not path.is_file():
                continue
            expected_hash = str(item.get("sha256", "")).lower()
            if len(expected_hash) != 64 or sha256_file(path).lower() != expected_hash:
                raise ValueError(f"Working-copy integrity check failed: {relative_path}")

            # 1. Resumability check: if already analyzed in a previous run, reuse directly
            if relative_path in existing_results_map:
                entry = existing_results_map[relative_path]
                results.append(entry)
                continue

            # 2. Exact SHA-256 Deduplication: reuse extraction from identical document
            file_sha = item.get("sha256")
            if file_sha and file_sha in sha256_cache:
                cached = sha256_cache[file_sha]
                entry = {
                    "relative_path": item["relative_path"],
                    "filename": item["filename"],
                    "extension": item["extension"],
                    "sha256": item["sha256"],
                    "extraction_method": f"{cached.get('extraction_method', 'extracted')}_dedup",
                    "text_length": cached.get("text_length", 0),
                    "language": cached.get("language"),
                    "metadata": cached.get("metadata", {}),
                    "text_preview": cached.get("text_preview", ""),
                    "deduplicated_from": cached.get("relative_path"),
                }
                results.append(entry)
                existing_results_map[relative_path] = entry
                continue

            # 3. Content extraction with Unicode NFC normalization
            text, method = self._extract_text(path)
            if text:
                text = unicodedata.normalize("NFC", text)
            language = method if method in {"mya", "eng", "mya+eng"} else None
            extraction_method = "ocr" if language else method
            metadata: Dict[str, Any] = {}
            if text.strip():
                try:
                    metadata = metadata_extractor.extract(text)
                except Exception as exc:
                    logger.warning("Metadata extraction failed for %s: %s", path, exc)

            entry = {
                "relative_path": item["relative_path"],
                "filename": item["filename"],
                "extension": item["extension"],
                "sha256": item["sha256"],
                "extraction_method": extraction_method,
                "text_length": len(text),
                "language": language,
                "metadata": metadata,
                "text_preview": text[:2000],
            }
            results.append(entry)
            existing_results_map[relative_path] = entry
            if file_sha:
                sha256_cache[file_sha] = entry

            batch_counter += 1
            if batch_counter % BATCH_FLUSH_INTERVAL == 0:
                checkpoint_payload = {
                    "schema_version": 1,
                    "session_id": session_id,
                    "analyzed_files": len(results),
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "ai_used": False,
                    "results": results,
                }
                self.workspace._write(session / "understanding.json", checkpoint_payload)
                gc.collect()

        result = {
            "schema_version": 1,
            "session_id": session_id,
            "analyzed_files": len(results),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "ai_used": False,
            "results": results,
        }
        self.workspace._write(session / "understanding.json", result)
        gc.collect()
        return {k: v for k, v in result.items() if k != "results"}


document_understanding_service = DocumentUnderstandingService(safe_workspace_service)
