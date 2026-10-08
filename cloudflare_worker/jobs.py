"""Durable D1 job ledger for Train 1 async work.

D1 is the authoritative durable store for job idempotency when a Cloudflare
D1 binding is provisioned. This module intentionally provides no lease takeover
or fencing; those belong to Train 3.

The caller must pass the same idempotency key through every external side
effect so duplicate delivery converges on one job outcome.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .d1 import D1Database

_KEY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
_MAX_KEY = 255
_MAX_JOB_TYPE = 100
_MAX_ATTEMPTS = 20


def _stamp(value: datetime | None = None) -> str:
    instant = value or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Job timestamps must be timezone-aware.")
    return instant.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_key(value: str) -> str:
    key = str(value).strip()
    if not 1 <= len(key) <= _MAX_KEY or any(char not in _KEY_CHARS for char in key):
        raise ValueError("Invalid job idempotency key.")
    return key


def _validate_job_type(value: str) -> str:
    job_type = str(value).strip()
    if not 1 <= len(job_type) <= _MAX_JOB_TYPE:
        raise ValueError("Invalid job type.")
    return job_type


def _payload_json(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ValueError("Job payload must be an object.")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_digest(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


CREATE_SQL = """
INSERT INTO jobs (
    id, organization_id, job_type, status, idempotency_key, payload_json, max_attempts
)
VALUES (?, ?, ?, 'pending', ?, ?, ?)
ON CONFLICT(idempotency_key) DO NOTHING
"""

GET_BY_KEY_SQL = """
SELECT id, organization_id, job_type, status, idempotency_key, payload_json,
       result_json, attempts, max_attempts, available_at, last_error
FROM jobs
WHERE idempotency_key = ?
"""

CLAIM_SQL = """
UPDATE jobs
SET status = 'processing',
    attempts = attempts + 1,
    updated_at = ?
WHERE id = (
    SELECT id
    FROM jobs
    WHERE status = 'pending'
      AND available_at <= ?
    ORDER BY created_at, id
    LIMIT 1
)
RETURNING id, organization_id, job_type, status, idempotency_key, payload_json,
          result_json, attempts, max_attempts, available_at, last_error
"""

SUCCEED_SQL = """
UPDATE jobs
SET status = 'succeeded',
    result_json = ?,
    last_error = NULL,
    updated_at = ?
WHERE id = ? AND status = 'processing'
"""

FAIL_SQL = """
UPDATE jobs
SET status = ?,
    available_at = ?,
    last_error = ?,
    updated_at = ?
WHERE id = ? AND status = 'processing'
"""


async def create_or_get_job(
    db: D1Database,
    *,
    job_id: str,
    job_type: str,
    idempotency_key: str,
    payload: dict[str, Any],
    organization_id: str | None = None,
    max_attempts: int = 5,
) -> dict[str, Any]:
    """Atomically create a job or return the existing idempotent job."""
    if not job_id or len(job_id) > 255:
        raise ValueError("Invalid job id.")
    job_type = _validate_job_type(job_type)
    idempotency_key = _validate_key(idempotency_key)
    if type(max_attempts) is not int or not 1 <= max_attempts <= _MAX_ATTEMPTS:
        raise ValueError("Invalid max_attempts.")
    encoded = _payload_json(payload)
    await db.execute(
        CREATE_SQL,
        (job_id, organization_id, job_type, idempotency_key, encoded, max_attempts),
    )
    row = await db.first(GET_BY_KEY_SQL, (idempotency_key,))
    if row is None:
        raise RuntimeError("Job creation did not return a durable record.")
    if row.get("job_type") != job_type:
        raise ValueError("Idempotency key is already bound to a different job type.")
    if row.get("payload_json") != encoded:
        raise ValueError("Idempotency key is already bound to a different payload.")
    return row


async def claim_next_job(
    db: D1Database,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Claim one pending job; no lease/takeover semantics are provided."""
    stamp = _stamp(now)
    return await db.first(CLAIM_SQL, (stamp, stamp))


async def mark_succeeded(
    db: D1Database,
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    job_id = job.get("id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("Invalid claimed job.")
    encoded = _payload_json(result)
    await db.execute(SUCCEED_SQL, (encoded, _stamp(now), job_id))


async def mark_failed(
    db: D1Database,
    job: dict[str, Any],
    *,
    retryable: bool,
    error: str,
    now: datetime | None = None,
) -> str:
    """Record a safe failure; retryable jobs return to pending, exhausted jobs become dead."""
    if not isinstance(error, str) or not error.strip() or len(error) > 500:
        raise ValueError("Invalid job error.")
    job_id = job.get("id")
    attempts = job.get("attempts")
    max_attempts = job.get("max_attempts")
    if (
        not isinstance(job_id, str) or not job_id
        or type(attempts) is not int or attempts < 1
        or type(max_attempts) is not int or not 1 <= max_attempts <= _MAX_ATTEMPTS
    ):
        raise ValueError("Invalid claimed job.")
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Job timestamps must be timezone-aware.")
    terminal = (not retryable) or attempts >= max_attempts
    status = "dead" if terminal else "pending"
    delay = min(3600, 30 * (2 ** min(attempts - 1, 7)))
    available = instant if terminal else instant + timedelta(seconds=delay)
    await db.execute(
        FAIL_SQL,
        (status, _stamp(available), error.strip(), _stamp(instant), job_id),
    )
    return status
