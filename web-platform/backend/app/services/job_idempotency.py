"""Durable job-level idempotency state contract.

This module is intentionally transport/worker agnostic. It provides the durable
state machine that a future queue adapter must use before late acknowledgements
or worker takeover are enabled.

The default backend is a single-node POSIX file store with atomic replacement
and an exclusive lock. It is suitable for deterministic local/contract tests;
it is NOT a distributed worker lease/fencing implementation.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

_ALLOWED_KEY = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TERMINAL = {"succeeded", "exhausted", "dead_lettered"}
_ACTIVE = {"received", "running", "retryable", "failed"}


@dataclass
class JobRecord:
    job_id: str
    idempotency_key: str
    status: str
    attempt: int = 0
    max_attempts: int = 3
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobIdempotencyStore:
    """Durable idempotency record store with atomic state transitions."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_key(key: str) -> str:
        key = str(key).strip()
        if not _ALLOWED_KEY.fullmatch(key):
            raise ValueError("Invalid idempotency key")
        return key

    def _path(self, key: str) -> Path:
        key = self.validate_key(key)
        return self.root / f"{key}.json"

    def _lock_path(self, key: str) -> Path:
        key = self.validate_key(key)
        return self.root / f".{key}.lock"

    @contextmanager
    def _lock(self, key: str):
        lock_file = open(self._lock_path(key), "a+")
        try:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def get(self, key: str) -> Optional[JobRecord]:
        path = self._path(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return JobRecord(**json.load(handle))

    def claim(
        self,
        job_id: str,
        idempotency_key: str,
        *,
        max_attempts: int = 3,
    ) -> tuple[JobRecord, bool]:
        """Claim a job exactly once.

        Returns (record, True) for a new claim. For an existing key, returns
        (existing record, False), allowing duplicate deliveries to reuse the
        durable outcome instead of executing side effects again.
        """
        key = self.validate_key(idempotency_key)
        if not job_id or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("Invalid job claim")
        with self._lock(key):
            existing = self.get(key)
            if existing is not None:
                if existing.job_id != job_id:
                    raise ValueError("Idempotency key is already bound to another job")
                return existing, False
            record = JobRecord(
                job_id=job_id,
                idempotency_key=key,
                status="received",
                max_attempts=max_attempts,
            )
            self._save(record)
            return record, True

    def start(self, key: str) -> JobRecord:
        with self._lock(key):
            record = self._require(key)
            if record.status in _TERMINAL:
                return record
            if record.status not in {"received", "retryable"}:
                raise ValueError(f"Cannot start job from {record.status}")
            record.attempt += 1
            if record.attempt > record.max_attempts:
                record.status = "exhausted"
                self._save(record)
                return record
            record.status = "running"
            record.error = None
            self._save(record)
            return record

    def succeed(self, key: str, result: Optional[Dict[str, Any]] = None) -> JobRecord:
        with self._lock(key):
            record = self._require(key)
            if record.status == "succeeded":
                return record
            if record.status in {"exhausted", "dead_lettered"}:
                raise ValueError(f"Cannot succeed terminal job in {record.status}")
            if record.status != "running":
                raise ValueError(f"Cannot succeed job from {record.status}")
            record.status = "succeeded"
            record.result = result or {}
            record.error = None
            self._save(record)
            return record

    def fail(self, key: str, error: str, *, retryable: bool) -> JobRecord:
        with self._lock(key):
            record = self._require(key)
            if record.status in _TERMINAL:
                return record
            if record.status != "running":
                raise ValueError(f"Cannot fail job from {record.status}")
            record.error = str(error)
            if retryable and record.attempt < record.max_attempts:
                record.status = "retryable"
            else:
                record.status = "exhausted"
            self._save(record)
            return record

    def dead_letter(self, key: str, reason: str) -> JobRecord:
        with self._lock(key):
            record = self._require(key)
            if record.status == "dead_lettered":
                return record
            if record.status != "exhausted":
                raise ValueError("Only exhausted jobs can enter the DLQ")
            record.status = "dead_lettered"
            record.error = str(reason)
            self._save(record)
            return record

    def _require(self, key: str) -> JobRecord:
        record = self.get(key)
        if record is None:
            raise KeyError("Job idempotency record not found")
        return record

    def _save(self, record: JobRecord) -> None:
        target = self._path(record.idempotency_key)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{record.idempotency_key}.",
            suffix=".tmp",
            dir=str(self.root),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(asdict(record), handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
