from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import threading
import time
import zipfile
import errno
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterator

from app.core.config import settings
from app.services.safe_workspace_service import (
    is_session_coordination_file,
    safe_workspace_service,
)

_HASH_CHUNK_SIZE = 1024 * 1024
_MAX_RESTORE_ENTRIES = 100_000
_MAX_RESTORE_TOTAL_BYTES = 100 * 1024 * 1024 * 1024
_MAX_RESTORE_MEMBER_BYTES = 20 * 1024 * 1024 * 1024
_MAX_RESTORE_COMPRESSION_RATIO = 10_000
_BACKUP_OPERATION_GUARD = threading.Lock()
_SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


class WorkspaceBackupService:
    """Create restorable snapshots of the writable DMS workspace only."""

    @contextmanager
    def _backup_operation_lock(self, root: Path) -> Iterator[None]:
        """Serialize backup mutations in this process and across processes."""
        lock_path = root / ".backup-operation.lock"
        with _BACKUP_OPERATION_GUARD:
            if lock_path.is_symlink():
                raise ValueError("Backup operation lock cannot be a symlink.")
            flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(lock_path, flags, 0o600)
            locked = False
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise ValueError("Backup operation lock must be a regular file.")
                if os.name == "nt":
                    import msvcrt

                    while True:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        try:
                            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                            break
                        except OSError as exc:
                            contended = exc.errno in {
                                errno.EACCES, errno.EAGAIN, errno.EDEADLK,
                            } or getattr(exc, "winerror", None) in {33, 36}
                            if not contended:
                                raise
                            time.sleep(0.01)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_EX)
                locked = True
                yield
            finally:
                try:
                    if locked:
                        if os.name == "nt":
                            import msvcrt

                            os.lseek(descriptor, 0, os.SEEK_SET)
                            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl

                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def _validated_backup_file(self, root: Path, name: str) -> Path:
        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Backup metadata contains an invalid filename.")
        path = root / name
        if path.is_symlink():
            raise ValueError("Backup retention cannot inspect symlinked files.")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError("Backup retention encountered a path outside BACKUP_ROOT.") from exc
        if resolved.parent != root or not stat.S_ISREG(resolved.stat().st_mode):
            raise ValueError("Backup retention encountered a non-regular file.")
        return resolved

    def _retention_records(self, root: Path) -> list[dict[str, Any]]:
        archives: dict[str, Path] = {}
        manifests: dict[str, Path] = {}
        for path in root.iterdir():
            if path.name == ".backup-operation.lock":
                continue
            if not path.name.startswith("workspace_"):
                continue
            if path.suffix.lower() not in {".zip", ".json"}:
                continue
            if path.is_symlink():
                raise ValueError("Backup retention cannot inspect symlinked files.")
            validated = self._validated_backup_file(root, path.name)
            stem = path.stem
            target = archives if path.suffix.lower() == ".zip" else manifests
            if stem in target:
                raise ValueError("Backup retention found duplicate backup entries.")
            target[stem] = validated

        if set(archives) != set(manifests):
            raise ValueError("Backup retention found an incomplete archive/manifest pair.")

        records = []
        for stem, archive in archives.items():
            manifest_path = manifests[stem]
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError) as exc:
                raise ValueError("Backup retention found unreadable or invalid metadata.") from exc
            if not isinstance(manifest, dict):
                raise ValueError("Backup retention found invalid metadata.")
            digest = manifest.get("sha256")
            created_at = manifest.get("created_at")
            archive_name = manifest.get("archive")
            if (
                manifest.get("schema_version") != 1
                or not isinstance(digest, str)
                or _SHA256_PATTERN.fullmatch(digest) is None
                or not isinstance(created_at, str)
                or not isinstance(archive_name, str)
                or Path(archive_name).name != archive.name
            ):
                raise ValueError("Backup retention found incomplete metadata.")
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("Backup retention found an invalid creation time.") from exc
            if created.tzinfo is None or created.utcoffset() is None:
                raise ValueError("Backup retention found a timezone-naive creation time.")
            if _sha256(archive).lower() != digest.lower():
                raise ValueError("Backup retention found an archive that failed integrity verification.")
            if not zipfile.is_zipfile(archive):
                raise ValueError("Backup retention found an invalid archive.")
            records.append({
                "archive": archive,
                "manifest": manifest_path,
                "created_at": created.astimezone(timezone.utc),
            })
        return sorted(
            records,
            key=lambda record: (record["created_at"], record["archive"].name),
            reverse=True,
        )

    def _backup_root(self) -> Path:
        configured_root = Path(settings.BACKUP_ROOT).expanduser()
        if configured_root.is_symlink():
            raise ValueError("BACKUP_ROOT cannot be a symlink.")
        root = configured_root.resolve()
        protected_roots = [Path(settings.WORKING_ROOT).resolve()]
        if settings.SOURCE_ROOT:
            protected_roots.append(Path(settings.SOURCE_ROOT).expanduser().resolve())
        for protected in protected_roots:
            if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
                raise ValueError("BACKUP_ROOT must not overlap SOURCE_ROOT or WORKING_ROOT.")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create(self, session_id: str | None = None) -> dict[str, Any]:
        source = safe_workspace_service.root.resolve()
        backup_root = self._backup_root()
        with self._backup_operation_lock(backup_root):
            return self._create_locked(source, backup_root, session_id)

    def _create_locked(
        self, source: Path, backup_root: Path, session_id: str | None
    ) -> dict[str, Any]:
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
                    if is_session_coordination_file(rel):
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

    def restore_to_recovery(
        self, archive_name: str, *, confirm: bool = False
    ) -> dict[str, Any]:
        if confirm is not True:
            raise ValueError("Restore requires explicit confirmation.")
        backup_root = self._backup_root()
        with self._backup_operation_lock(backup_root):
            return self._restore_to_recovery_locked(archive_name)

    def _restore_to_recovery_locked(self, archive_name: str) -> dict[str, Any]:
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
                    raw_parts = name.rstrip("/").split("/") if name else []
                    windows_reserved = {"CON", "PRN", "AUX", "NUL"} | {
                        f"{prefix}{number}"
                        for prefix in ("COM", "LPT")
                        for number in range(1, 10)
                    }
                    if (
                        not name
                        or "\\" in name
                        or any(ord(char) < 32 for char in name)
                        or posix_path.is_absolute()
                        or windows_path.is_absolute()
                        or windows_path.drive
                        or any(part in {"", ".", ".."} for part in raw_parts)
                        or any(
                            ":" in part
                            or part.endswith((" ", "."))
                            or part.split(".", 1)[0].upper() in windows_reserved
                            for part in raw_parts
                        )
                    ):
                        raise ValueError("Backup contains an unsafe path.")
                    normalized_name = "/".join(raw_parts)
                    collision_key = normalized_name.casefold()
                    if collision_key in seen_paths:
                        raise ValueError("Backup contains duplicate or case-colliding paths.")
                    seen_paths.add(collision_key)

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

    def prune(self, *, confirm: bool = False, dry_run: bool = False) -> dict[str, Any]:
        if dry_run is not True and confirm is not True:
            raise ValueError("Pruning backups requires explicit confirmation.")
        root = self._backup_root()
        with self._backup_operation_lock(root):
            records = self._retention_records(root)
            minimum = max(1, int(settings.BACKUP_MINIMUM_RETAINED))
            cutoff = datetime.now(timezone.utc).timestamp() - settings.BACKUP_RETENTION_DAYS * 86400
            protected = {record["archive"].name for record in records[:minimum]}
            retained = []
            candidates = []
            for record in records:
                archive_name = record["archive"].name
                if archive_name in protected or record["created_at"].timestamp() >= cutoff:
                    retained.append(record)
                else:
                    candidates.append(record)

            removed: list[str] = []
            if not dry_run:
                # The plan is rebuilt under the cross-process lock at execution time.
                for record in candidates:
                    archive = self._validated_backup_file(root, record["archive"].name)
                    manifest = self._validated_backup_file(root, record["manifest"].name)
                    archive.unlink()
                    manifest.unlink()
                    removed.append(archive.name)

            return {
                "retention_days": settings.BACKUP_RETENTION_DAYS,
                "minimum_retained": minimum,
                "dry_run": dry_run,
                "retained": [record["archive"].name for record in retained],
                "would_remove": [record["archive"].name for record in candidates],
                "removed": removed,
            }


workspace_backup_service = WorkspaceBackupService()
