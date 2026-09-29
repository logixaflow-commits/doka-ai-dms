from __future__ import annotations

import hashlib
import json
import shutil
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
        archive_base = backup_root / f"workspace_{timestamp}"
        archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=source))
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

    def prune(self) -> dict[str, Any]:
        root = self._backup_root()
        cutoff = datetime.now(timezone.utc).timestamp() - settings.BACKUP_RETENTION_DAYS * 86400
        removed = []
        for path in root.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed.append(path.name)
        return {"retention_days": settings.BACKUP_RETENTION_DAYS, "removed": removed}


workspace_backup_service = WorkspaceBackupService()
