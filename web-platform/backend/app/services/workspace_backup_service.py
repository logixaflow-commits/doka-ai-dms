from __future__ import annotations

import hashlib
import json
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from app.core.config import settings
from app.services.safe_workspace_service import safe_workspace_service

_HASH_CHUNK_SIZE = 1024 * 1024
_MAX_RESTORE_ENTRIES = 100_000
_MAX_RESTORE_TOTAL_BYTES = 100 * 1024 * 1024 * 1024
_MAX_RESTORE_MEMBER_BYTES = 20 * 1024 * 1024 * 1024
_MAX_RESTORE_COMPRESSION_RATIO = 10_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


class WorkspaceBackupService:
    """Create restorable snapshots of the writable DMS workspace only."""

    def _backup_root(self) -> Path:
        root = settings.BACKUP_ROOT.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create(self, session_id: str | None = None) -> dict[str, Any]:
        source = safe_workspace_service.root.resolve()
        backup_root = self._backup_root()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        archive = backup_root / f"workspace_{timestamp}.zip"
        temporary_archive = archive.with_suffix(".zip.tmp")

        # Snapshot only regular files inside the active writable workspace.
        # Symlinks are excluded so a workspace link cannot pull source-drive or
        # other out-of-workspace data into the backup.
        try:
            with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for path in source.rglob("*"):
                    if path.is_symlink() or not path.is_file():
                        continue
                    try:
                        path.resolve().relative_to(source)
                    except ValueError:
                        continue
                    rel = path.relative_to(source)
                    if rel.parts and rel.parts[0] == "Recovery":
                        continue
                    if path.name.endswith(".tmp"):
                        continue
                    zf.write(path, rel.as_posix())
            temporary_archive.replace(archive)
        except Exception:
            temporary_archive.unlink(missing_ok=True)
            raise

        digest = _sha256(archive)
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "archive": str(archive),
            "sha256": digest,
            "session_id": session_id,
        }
        manifest_path = archive.with_suffix(".json")
        temporary_manifest = manifest_path.with_suffix(".json.tmp")
        temporary_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_manifest.replace(manifest_path)
        return manifest

    def list_backups(self) -> list[dict[str, Any]]:
        root = self._backup_root()
        result = []
        for manifest_path in sorted(root.glob("workspace_*.json"), reverse=True):
            try:
                result.append(json.loads(manifest_path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return result

    def _resolve_archive(self, archive_name: str) -> Path:
        # Accept a filename, not an arbitrary path supplied by an API caller.
        if not archive_name or Path(archive_name).name != archive_name or "/" in archive_name or "\\" in archive_name:
            raise ValueError("Invalid backup archive name.")
        root = self._backup_root()
        archive = (root / archive_name).resolve()
        try:
            archive.relative_to(root)
        except ValueError as exc:
            raise ValueError("Backup path is outside BACKUP_ROOT.") from exc
        if not archive.is_file() or archive.suffix != ".zip":
            raise ValueError("Backup archive does not exist.")
        return archive

    def verify(self, archive_name: str) -> dict[str, Any]:
        archive = self._resolve_archive(archive_name)
        manifest_path = archive.with_suffix(".json")
        if not manifest_path.is_file():
            raise ValueError("Backup manifest is missing; integrity cannot be verified.")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Backup manifest is invalid.") from exc
        expected = str(manifest.get("sha256", "")).lower()
        if len(expected) != 64:
            raise ValueError("Backup manifest SHA-256 is missing or invalid.")
        digest = _sha256(archive)
        return {
            "archive": str(archive),
            "sha256": digest,
            "verified": digest == expected,
        }

    def restore_to_recovery(self, archive_name: str) -> dict[str, Any]:
        archive = self._resolve_archive(archive_name)
        verification = self.verify(archive.name)
        if not verification["verified"]:
            raise ValueError("Backup integrity verification failed; restore was stopped.")

        workspace_root = settings.WORKING_ROOT.resolve()
        recovery_root = workspace_root / "Recovery"
        if recovery_root.is_symlink():
            raise ValueError("Recovery directory cannot be a symlink.")
        recovery_root.mkdir(parents=True, exist_ok=True)
        try:
            recovery_root.resolve().relative_to(workspace_root)
        except ValueError as exc:
            raise ValueError("Recovery directory is outside WORKING_ROOT.") from exc
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = recovery_root / f"restore_{stamp}"
        target.mkdir(parents=True, exist_ok=False)

        try:
            with zipfile.ZipFile(archive) as zf:
                members = zf.infolist()
                if len(members) > _MAX_RESTORE_ENTRIES:
                    raise ValueError("Backup contains too many entries to restore safely.")
                total_uncompressed = 0
                seen_paths: set[str] = set()
                for member in members:
                    # ZIP names use POSIX separators. Reject Windows separators,
                    # drive paths, absolute paths and parent traversal on every OS.
                    name = member.filename
                    posix_path = PurePosixPath(name)
                    windows_path = PureWindowsPath(name)
                    if (
                        not name
                        or "\\" in name
                        or posix_path.is_absolute()
                        or windows_path.is_absolute()
                        or windows_path.drive
                        or ".." in posix_path.parts
                    ):
                        raise ValueError("Backup contains an unsafe path.")
                    normalized_name = posix_path.as_posix().rstrip("/")
                    if normalized_name in seen_paths:
                        raise ValueError("Backup contains duplicate paths.")
                    seen_paths.add(normalized_name)

                    member_mode = (member.external_attr >> 16) & 0o170000
                    if member_mode == stat.S_IFLNK or member_mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                        raise ValueError("Backup contains an unsupported filesystem entry.")
                    if member.flag_bits & 0x1:
                        raise ValueError("Encrypted backup entries are not supported.")
                    if member.file_size > _MAX_RESTORE_MEMBER_BYTES:
                        raise ValueError("Backup contains a file that exceeds the restore size limit.")
                    total_uncompressed += member.file_size
                    if total_uncompressed > _MAX_RESTORE_TOTAL_BYTES:
                        raise ValueError("Backup exceeds the total restore size limit.")
                    if member.file_size and (
                        member.compress_size == 0
                        or member.file_size / member.compress_size > _MAX_RESTORE_COMPRESSION_RATIO
                    ):
                        raise ValueError("Backup contains an unsafe compression ratio.")

                    member_path = (target / Path(*posix_path.parts)).resolve()
                    try:
                        member_path.relative_to(target)
                    except ValueError as exc:
                        raise ValueError("Backup contains an unsafe path.") from exc
                zf.extractall(target)
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise

        return {
            "archive": str(archive),
            "recovery_path": str(target),
            "active_workspace_changed": False,
        }

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
