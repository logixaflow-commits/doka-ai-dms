from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.safe_workspace_service import safe_workspace_service


class WorkspaceBackupService:
    """Create restorable snapshots of the writable DMS workspace only."""

    def _backup_root(self) -> Path:
        root = settings.BACKUP_ROOT.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create(self, session_id: str | None = None) -> dict[str, Any]:
        source = safe_workspace_service.root.resolve()
        backup_root = self._backup_root()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = backup_root / f"workspace_{timestamp}.zip"
        # Snapshot only the active writable workspace. Recovery copies are derived
        # artifacts and must not recursively inflate future backups.
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in source.rglob("*"):
                if path.is_dir():
                    continue
                rel = path.relative_to(source)
                if rel.parts and rel.parts[0] == "Recovery":
                    continue
                if path.name.endswith(".tmp"):
                    continue
                zf.write(path, rel.as_posix())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "archive": str(archive),
            "sha256": digest,
            "session_id": session_id,
        }
        manifest_path = archive.with_suffix(".json")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def list_backups(self) -> list[dict[str, Any]]:
        root = self._backup_root()
        result = []
        for manifest_path in sorted(root.glob("workspace_*.json"), reverse=True):
            try:
                result.append(json.loads(manifest_path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return result

    def verify(self, archive_name: str) -> dict[str, Any]:
        root = self._backup_root()
        archive = (root / archive_name).resolve()
        try:
            archive.relative_to(root)
        except ValueError as exc:
            raise ValueError("Backup path is outside BACKUP_ROOT.") from exc
        if not archive.is_file() or archive.suffix != ".zip":
            raise ValueError("Backup archive does not exist.")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest_path = archive.with_suffix(".json")
        expected = None
        if manifest_path.exists():
            expected = json.loads(manifest_path.read_text(encoding="utf-8")).get("sha256")
        return {"archive": str(archive), "sha256": digest, "verified": expected in (None, digest)}

    def restore_to_recovery(self, archive_name: str) -> dict[str, Any]:
        root = self._backup_root()
        archive = (root / archive_name).resolve()
        try:
            archive.relative_to(root)
        except ValueError as exc:
            raise ValueError("Backup path is outside BACKUP_ROOT.") from exc
        if not archive.is_file() or archive.suffix != ".zip":
            raise ValueError("Backup archive does not exist.")
        recovery_root = settings.WORKING_ROOT.resolve() / "Recovery"
        recovery_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = recovery_root / f"restore_{stamp}"
        target.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                member_path = (target / member.filename).resolve()
                try:
                    member_path.relative_to(target)
                except ValueError as exc:
                    shutil.rmtree(target, ignore_errors=True)
                    raise ValueError("Backup contains an unsafe path.") from exc
            zf.extractall(target)
        return {"archive": str(archive), "recovery_path": str(target), "active_workspace_changed": False}

    def prune(self) -> dict[str, Any]:
        root = self._backup_root()
        cutoff = datetime.now(timezone.utc).timestamp() - settings.BACKUP_RETENTION_DAYS * 86400
        removed = []
        for path in root.iterdir():
            if not path.is_file() or path.stat().st_mtime >= cutoff:
                continue
            if path.suffix.lower() not in {".zip", ".json"} or not path.name.startswith("workspace_"):
                continue
            path.unlink(missing_ok=True)
            removed.append(path.name)
        return {"retention_days": settings.BACKUP_RETENTION_DAYS, "removed": removed}


workspace_backup_service = WorkspaceBackupService()
