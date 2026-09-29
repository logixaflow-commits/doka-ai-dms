from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from loguru import logger
from app.core.config import settings

CHUNK_SIZE = 1024 * 1024


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

    def _dir(self, session_id: str) -> Path:
        return self.root / "imports" / session_id

    def _json_path(self, session_id: str, name: str) -> Path:
        return self._dir(session_id) / name

    def _read(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _write(self, path: Path, value: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _lock(self, session_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(session_id, threading.Lock())

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
        if settings.ORIGINAL_READ_ONLY and settings.ALLOW_SOURCE_WRITE:
            raise ValueError("Unsafe configuration: ALLOW_SOURCE_WRITE must remain false.")
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
            "files_total": 0, "files_copied": 0, "files_verified": 0,
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
            source = self.validate_source(Path(manifest["source_root"]))
            copy_root = Path(manifest["working_copy"]).resolve()
            copy_root.mkdir(parents=True, exist_ok=True)
            files = list(self._files(source))
            status.update({
                "state": "running", "files_total": len(files),
                "bytes_total": sum(p.stat().st_size for p in files if p.exists()),
                "updated_at": utc_now(), "error": None,
            })
            self._write(status_path, status)
            try:
                for src in files:
                    rel = src.relative_to(source).as_posix()
                    dest = copy_root / Path(rel)
                    try:
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
                    status["updated_at"] = utc_now()
                    self._write(manifest_path, manifest)
                    self._write(status_path, status)
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
            root = Path(manifest["working_copy"]).resolve()
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

    def status(self, session_id: str) -> Dict[str, Any]:
        value = self._read(self._json_path(session_id, "status.json"))
        if not value:
            raise ValueError(f"Unknown import session: {session_id}")
        return value

    def inventory(self, session_id: str, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
        value = self._read(self._json_path(session_id, "inventory.json"))
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
