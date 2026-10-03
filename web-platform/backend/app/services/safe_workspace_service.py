from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from loguru import logger
from app.core.config import settings

CHUNK_SIZE = 1024 * 1024
_SESSION_METADATA_FILES = {
    "status.json",
    "manifest.json",
    "inventory.json",
    "understanding.json",
    "ocr_corrections.json",
    "organization_plan.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SafeWorkspaceService:
    """Source is read-only; imports are verified copies; scans only read the copy."""

    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    @property
    def root(self) -> Path:
        root = settings.WORKING_ROOT.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _validate_session_id(self, session_id: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{32}", session_id or ""):
            raise ValueError(f"Invalid import session id: {session_id}")
        return session_id

    def _imports_dir(self) -> Path:
        root = self.root.resolve()
        imports_dir = root / "imports"
        if imports_dir.is_symlink():
            raise ValueError("Import sessions directory cannot be a symlink.")
        resolved = imports_dir.resolve()
        if resolved.parent != root:
            raise ValueError("Import sessions directory is outside the workspace.")
        if imports_dir.exists() and not imports_dir.is_dir():
            raise ValueError("Import sessions path must be a directory.")
        return imports_dir

    def _dir(self, session_id: str) -> Path:
        imports_root = self._imports_dir()
        session_dir = imports_root / self._validate_session_id(session_id)
        if session_dir.is_symlink():
            raise ValueError("Import session directory cannot be a symlink.")
        resolved = session_dir.resolve()
        if resolved.parent != imports_root.resolve():
            raise ValueError("Import session directory is outside the workspace.")
        if session_dir.exists() and not session_dir.is_dir():
            raise ValueError("Import session path must be a directory.")
        return session_dir

    def _json_path(self, session_id: str, name: str) -> Path:
        if name not in _SESSION_METADATA_FILES:
            raise ValueError("Invalid import-session metadata filename.")
        return self._validate_metadata_path(self._dir(session_id) / name)

    def _validate_metadata_path(self, path: Path) -> Path:
        root = self.root.resolve()
        candidate = Path(os.path.abspath(path))
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("Import-session metadata path is outside the workspace.") from exc
        if (
            len(relative.parts) != 3
            or relative.parts[0] != "imports"
            or relative.name not in _SESSION_METADATA_FILES
        ):
            raise ValueError("Invalid import-session metadata path.")

        session_dir = self._dir(relative.parts[1])
        if candidate.parent != session_dir:
            raise ValueError("Import-session metadata path is outside its session.")
        if candidate.is_symlink():
            raise ValueError("Import-session metadata file cannot be a symlink.")
        if candidate.exists() and candidate.resolve().parent != session_dir.resolve():
            raise ValueError("Import-session metadata file is outside its session.")
        return candidate

    def _validate_temporary_path(self, path: Path, target: Path) -> Path:
        target = self._validate_metadata_path(target)
        candidate = Path(os.path.abspath(path))
        if (
            candidate.parent != target.parent
            or not candidate.name.startswith(f".{target.name}.")
            or not candidate.name.endswith(".tmp")
        ):
            raise ValueError("Temporary import metadata path is outside its session.")
        if candidate.is_symlink():
            raise ValueError("Temporary import metadata file cannot be a symlink.")
        if candidate.exists() and candidate.resolve().parent != target.parent.resolve():
            raise ValueError("Temporary import metadata file is outside its session.")
        return candidate

    def validate_manifest_paths(self, session_id: str, manifest: Dict[str, Any]) -> tuple[Path, Path]:
        """Bind manifest paths to this session; never trust persisted absolute paths."""
        self._validate_session_id(session_id)
        session_root = self._dir(session_id).resolve()
        if manifest.get("session_id") != session_id:
            raise ValueError("Import manifest does not belong to this session.")
        copy_candidate = session_root / "source_copy"
        if copy_candidate.is_symlink():
            raise ValueError("Import working-copy directory cannot be a symlink.")
        expected_copy = copy_candidate.resolve()
        if expected_copy.parent != session_root:
            raise ValueError("Import working-copy directory is outside its session.")
        configured_copy = Path(str(manifest.get("working_copy", ""))).expanduser().resolve()
        if configured_copy != expected_copy:
            raise ValueError("Import manifest working-copy path is invalid.")
        source_value = manifest.get("source_root")
        if not source_value:
            raise ValueError("Import manifest source path is missing.")
        source = self.validate_source(Path(str(source_value)))
        return source, expected_copy

    def _read(self, path: Path) -> Dict[str, Any]:
        path = self._validate_metadata_path(path)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            return {}
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, path: Path, value: Dict[str, Any]) -> None:
        path = self._validate_metadata_path(path)
        if not path.parent.is_dir():
            raise ValueError("Import session directory does not exist.")
        legacy_tmp = path.with_suffix(path.suffix + ".tmp")
        if legacy_tmp.is_symlink():
            raise ValueError("Temporary import metadata file cannot be a symlink.")
        if path.is_symlink():
            raise ValueError("Import-session metadata file cannot be a symlink.")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            path = self._validate_metadata_path(path)
            temporary_path = self._validate_temporary_path(temporary_path, path)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _lock(self, session_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(session_id, threading.Lock())

    def _working_copy_destination(self, copy_root: Path, relative_path: str) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("Source file has an unsafe relative path.")
        destination = copy_root / relative
        if destination.is_symlink():
            raise ValueError("Working-copy destination cannot be a symlink.")
        current = destination.parent
        while current != copy_root:
            if current.is_symlink():
                raise ValueError("Working-copy parent directory cannot be a symlink.")
            if copy_root not in current.parents:
                raise ValueError("Working-copy destination is outside the import session.")
            current = current.parent
        try:
            destination.resolve().relative_to(copy_root)
        except ValueError as exc:
            raise ValueError("Working-copy destination is outside the import session.") from exc
        return destination

    def validate_source(self, source: Path) -> Path:
        source = source.expanduser().resolve()
        if not source.is_dir():
            raise ValueError(f"Source folder does not exist: {source}")
        working = self.root
        try:
            overlap = source == working or source.is_relative_to(working) or working.is_relative_to(source)
        except AttributeError:
            overlap = source == working or str(source).startswith(str(working) + os.sep) or str(working).startswith(str(source) + os.sep)
        if overlap:
            raise ValueError("Source folder cannot overlap the writable workspace.")
        if settings.ALLOW_SOURCE_WRITE:
            raise ValueError("Unsafe configuration: ALLOW_SOURCE_WRITE must remain false.")
        if not settings.ORIGINAL_READ_ONLY:
            raise ValueError("Unsafe configuration: ORIGINAL_READ_ONLY must remain true.")
        return source

    def create_import(self, source: Optional[str] = None) -> Dict[str, Any]:
        configured = Path(source) if source else settings.SOURCE_ROOT
        if configured is None:
            raise ValueError("SOURCE_ROOT is not configured.")
        source_path = self.validate_source(configured)
        session_id = uuid.uuid4().hex
        session = self._dir(session_id)
        session.mkdir(parents=True, exist_ok=False)
        copy_root = session / "source_copy"
        status = {
            "session_id": session_id, "state": "created",
            "source_root": str(source_path), "working_copy": str(copy_root),
            "started_at": utc_now(), "updated_at": utc_now(),
            "files_total": 0, "files_copied": 0, "progress": 0.0, "files_verified": 0,
            "files_failed": 0, "bytes_total": 0, "bytes_copied": 0, "error": None,
        }
        self._write(self._json_path(session_id, "status.json"), status)
        self._write(self._json_path(session_id, "manifest.json"), {
            "schema_version": 1, "session_id": session_id,
            "source_root": str(source_path), "working_copy": str(copy_root),
            "created_at": utc_now(), "files": {},
        })
        return status

    def _files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink():
                    yield path
            except OSError as exc:
                logger.warning("Cannot inspect %s: %s", path, exc)

    def run_import(self, session_id: str) -> Dict[str, Any]:
        status_path = self._json_path(session_id, "status.json")
        manifest_path = self._json_path(session_id, "manifest.json")
        if not status_path.exists() or not manifest_path.exists():
            raise ValueError(f"Unknown import session: {session_id}")
        with self._lock(session_id):
            status = self._read(status_path)
            manifest = self._read(manifest_path)
            source, copy_root = self.validate_manifest_paths(session_id, manifest)
            if copy_root.is_symlink():
                raise ValueError("Import working-copy directory cannot be a symlink.")
            copy_root.mkdir(parents=True, exist_ok=True)
            files = list(self._files(source))
            status.update({
                "state": "running", "files_total": len(files),
                "files_copied": 0, "files_verified": 0, "files_failed": 0,
                "bytes_total": sum(p.stat().st_size for p in files if p.exists()),
                "bytes_copied": 0, "progress": 0.0,
                "updated_at": utc_now(), "error": None,
            })
            self._write(status_path, status)
            try:
                for src in files:
                    rel = src.relative_to(source).as_posix()
                    try:
                        dest = self._working_copy_destination(copy_root, rel)
                        if src.is_symlink():
                            raise ValueError("Source file became a symlink during import.")
                        try:
                            src.resolve().relative_to(source)
                        except ValueError as exc:
                            raise ValueError("Source file escaped the selected source directory.") from exc
                        st = src.stat()
                        old = manifest["files"].get(rel)
                        if (old and old.get("size") == st.st_size and
                            old.get("source_mtime_ns") == st.st_mtime_ns and
                            old.get("verified") and dest.exists() and
                            sha256_file(dest) == old.get("sha256")):
                            status["files_verified"] += 1
                            status["bytes_copied"] += st.st_size
                            continue
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest = self._working_copy_destination(copy_root, rel)
                        shutil.copy2(src, dest)
                        source_hash = sha256_file(src)
                        if sha256_file(dest) != source_hash:
                            raise IOError("SHA-256 verification failed")
                        manifest["files"][rel] = {
                            "relative_path": rel, "source_path": str(src),
                            "working_path": str(dest), "filename": src.name,
                            "extension": src.suffix.lower(), "size": st.st_size,
                            "source_mtime_ns": st.st_mtime_ns,
                            "created_at": datetime.fromtimestamp(st.st_ctime, timezone.utc).isoformat(),
                            "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                            "sha256": source_hash, "verified": True, "status": "copied",
                        }
                        status["files_copied"] += 1
                        status["files_verified"] += 1
                        status["bytes_copied"] += st.st_size
                    except Exception as exc:
                        manifest["files"][rel] = {
                            "relative_path": rel, "source_path": str(src),
                            "filename": src.name, "extension": src.suffix.lower(),
                            "verified": False, "status": "failed", "error": str(exc),
                        }
                        status["files_failed"] += 1
                        logger.exception("Import failed for %s", src)
                    status["progress"] = (status["files_verified"] / len(files)) if files else 1.0
                    status["updated_at"] = utc_now()
                    self._write(manifest_path, manifest)
                    self._write(status_path, status)
                status["progress"] = 1.0
                status["state"] = "completed" if status["files_failed"] == 0 else "completed_with_errors"
            except Exception as exc:
                status["state"] = "failed"
                status["error"] = str(exc)
                logger.exception("Import session failed: %s", session_id)
            finally:
                status["updated_at"] = utc_now()
                self._write(manifest_path, manifest)
                self._write(status_path, status)
            return status

    def scan(self, session_id: str) -> Dict[str, Any]:
        session = self._dir(session_id)
        manifest_path = session / "manifest.json"
        status_path = session / "status.json"
        if not manifest_path.exists() or not status_path.exists():
            raise ValueError(f"Unknown import session: {session_id}")
        with self._lock(session_id):
            manifest = self._read(manifest_path)
            status = self._read(status_path)
            if status.get("state") not in {"completed", "completed_with_errors", "scanned"}:
                raise ValueError("Import is not complete. Finish the safe import before scanning.")
            _source, root = self.validate_manifest_paths(session_id, manifest)
            if not root.is_dir():
                raise ValueError("Working copy does not exist.")
            inventory, unreadable = [], []
            hashes: Dict[str, list] = {}
            names: Dict[str, list] = {}
            for path in self._files(root):
                rel = path.relative_to(root).as_posix()
                try:
                    st = path.stat()
                    digest = sha256_file(path)
                    item = {
                        "relative_path": rel, "filename": path.name,
                        "extension": path.suffix.lower(), "size": st.st_size,
                        "created_at": datetime.fromtimestamp(st.st_ctime, timezone.utc).isoformat(),
                        "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                        "sha256": digest, "readable": True, "status": "indexed",
                    }
                    inventory.append(item)
                    hashes.setdefault(digest, []).append(rel)
                    names.setdefault(path.name.casefold(), []).append(rel)
                except Exception as exc:
                    unreadable.append({"relative_path": rel, "filename": path.name,
                                       "readable": False, "status": "unreadable", "error": str(exc)})
            duplicate_groups = [v for v in hashes.values() if len(v) > 1]
            collisions = [v for v in names.values() if len(v) > 1]
            result = {
                "schema_version": 1, "session_id": session_id, "scanned_at": utc_now(),
                "working_copy": str(root), "files_total": len(inventory) + len(unreadable),
                "files_readable": len(inventory), "files_unreadable": len(unreadable),
                "exact_duplicate_groups": len(duplicate_groups),
                "exact_duplicate_files": sum(map(len, duplicate_groups)),
                "filename_collision_groups": len(collisions),
                "inventory": inventory, "unreadable": unreadable,
                "duplicate_groups": duplicate_groups, "filename_collision_groups_detail": collisions,
            }
            self._write(session / "inventory.json", result)
            status = self._read(status_path)
            status.update({
                "state": "scanned", "updated_at": utc_now(),
                "files_total": result["files_total"], "files_verified": result["files_readable"],
                "files_failed": result["files_unreadable"],
                "exact_duplicate_groups": result["exact_duplicate_groups"],
                "filename_collision_groups": result["filename_collision_groups"],
            })
            self._write(status_path, status)
            return {k: v for k, v in result.items() if k not in {
                "inventory", "unreadable", "duplicate_groups", "filename_collision_groups_detail"
            }}

    def search(
        self,
        session_id: str,
        query: str,
        limit: int = 100,
        extension: Optional[str] = None,
        category: Optional[str] = None,
        review_only: bool = False,
    ) -> Dict[str, Any]:
        inventory_path = self._json_path(session_id, "inventory.json")
        if not inventory_path.exists():
            raise ValueError("Inventory is not available. Run scan first.")
        with self._lock(session_id):
            value = self._read(inventory_path)
            understanding = self._read(self._json_path(session_id, "understanding.json"))
            corrections = self._read(self._json_path(session_id, "ocr_corrections.json"))
        if not value:
            raise ValueError("Inventory is not available. Run scan first.")
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000.")

        q = query.casefold().strip()
        extension_filter = extension.casefold().strip() if extension else ""
        category_filter = category.casefold().strip() if category else ""
        understood = {x.get("relative_path"): x for x in understanding.get("results", [])}
        corrected = corrections.get("results", {})

        results = []
        total_matches = 0
        for item in value.get("inventory", []):
            rel = item.get("relative_path", "")
            enriched = understood.get(rel, {})
            metadata = enriched.get("metadata", {}) if isinstance(enriched.get("metadata", {}), dict) else {}
            corrected_text = corrected.get(rel, "")
            category_value = str(metadata.get("category") or metadata.get("document_type") or "").casefold()

            if extension_filter and str(item.get("extension", "")).casefold() != extension_filter:
                continue
            if category_filter and category_filter not in category_value:
                continue
            if review_only and not (
                bool(enriched.get("review_required"))
                or enriched.get("extraction_method") in {"ocr_failed", "text_unreadable"}
            ):
                continue

            haystack = " ".join([
                item.get("filename", ""),
                rel,
                enriched.get("text_preview", ""),
                corrected_text,
                json.dumps(metadata, ensure_ascii=False),
            ]).casefold()
            if q and q not in haystack:
                continue

            total_matches += 1
            if len(results) < limit:
                results.append({
                    "relative_path": rel,
                    "filename": item.get("filename"),
                    "extension": item.get("extension"),
                    "size": item.get("size"),
                    "sha256": item.get("sha256"),
                    "modified_at": item.get("modified_at"),
                    "category": metadata.get("document_type") or metadata.get("category"),
                    "text_preview": (corrected_text or enriched.get("text_preview", ""))[:500],
                    "ocr_corrected": bool(corrected_text),
                })

        return {
            "session_id": session_id,
            "query": query,
            "filters": {
                "extension": extension,
                "category": category,
                "review_only": review_only,
            },
            "total": total_matches,
            "results": results,
        }

    def list_sessions(self, limit: int = 50) -> list[Dict[str, Any]]:
        imports_root = self._imports_dir()
        if not imports_root.exists():
            return []
        sessions = []
        for session_dir in imports_root.iterdir():
            if not re.fullmatch(r"[0-9a-f]{32}", session_dir.name):
                continue
            session_dir = self._dir(session_dir.name)
            if not session_dir.is_dir():
                continue
            with self._lock(session_dir.name):
                status = self._read(self._json_path(session_dir.name, "status.json"))
            if status:
                sessions.append({
                    "session_id": session_dir.name,
                    "state": status.get("state", "unknown"),
                    "source_root": status.get("source_root"),
                    "files_total": status.get("files_total", 0),
                    "files_verified": status.get("files_verified", 0),
                    "files_failed": status.get("files_failed", 0),
                    "progress": status.get("progress", 0.0),
                    "updated_at": status.get("updated_at"),
                })
        sessions.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return sessions[:limit]

    def status(self, session_id: str) -> Dict[str, Any]:
        status_path = self._json_path(session_id, "status.json")
        if not status_path.exists():
            raise ValueError(f"Unknown import session: {session_id}")
        with self._lock(session_id):
            value = self._read(status_path)
        if not value:
            raise ValueError(f"Unknown import session: {session_id}")
        return value

    def get_understanding(self, session_id: str) -> Dict[str, Any]:
        session = self._dir(session_id)
        understanding_path = session / "understanding.json"
        if not understanding_path.exists():
            raise ValueError("Understanding is not available. Run Read / OCR first.")
        with self._lock(session_id):
            value = self._read(understanding_path)
            if not value:
                raise ValueError("Understanding is not available. Run Read / OCR first.")
            corrections = self._read(session / "ocr_corrections.json")
            for item in value.get("results", []):
                relative_path = item.get("relative_path")
                if relative_path in corrections.get("results", {}):
                    item["corrected_text"] = corrections["results"][relative_path]
                    item["ocr_corrected"] = True
            return value

    def inventory(self, session_id: str, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
        inventory_path = self._json_path(session_id, "inventory.json")
        if not inventory_path.exists():
            raise ValueError("Inventory is not available. Run scan first.")
        with self._lock(session_id):
            value = self._read(inventory_path)
        if not value:
            raise ValueError("Inventory is not available. Run scan first.")
        items = value.get("inventory", [])
        return {
            "session_id": session_id, "total": len(items),
            "offset": offset, "limit": limit, "items": items[offset:offset + limit],
            "unreadable": value.get("unreadable", []),
            "duplicate_groups": value.get("duplicate_groups", []),
            "filename_collision_groups": value.get("filename_collision_groups_detail", []),
        }


safe_workspace_service = SafeWorkspaceService()
