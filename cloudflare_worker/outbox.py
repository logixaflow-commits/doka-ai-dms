"""Leased, idempotent dispatcher for the D1 transactional outbox.

The QStash message contains only an event ID. Consumers load the bounded
metadata from D1 after verifying the QStash signature; document bytes and
credentials never enter queue payloads.
"""
from __future__ import annotations

import inspect
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from .d1 import D1Database


def _is_retryable(error: BaseException) -> bool:
    """Retry only transient transport/provider failures; fail closed otherwise."""
    explicit = getattr(error, "retryable", None)
    if explicit is True:
        return True
    if explicit is False:
        return False
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", 0)
    return status == 408 or status == 429 or 500 <= status <= 599


class OutboxError(RuntimeError):
    """Safe outbox operation failure."""


CLAIM_SQL = """
UPDATE outbox_events
SET status = 'processing',
    attempts = attempts + 1,
    lease_until = ?,
    lease_token = ?
WHERE id = (
    SELECT id
    FROM outbox_events
    WHERE (
        status = 'pending'
        OR (status = 'processing' AND lease_until <= ?)
    )
      AND available_at <= ?
    ORDER BY created_at, id
    LIMIT 1
)
RETURNING id, event_type, aggregate_type, aggregate_id, attempts, max_attempts, lease_token
"""

DELIVER_SQL = """
UPDATE outbox_events
SET status = 'delivered',
    delivered_at = ?,
    lease_until = NULL,
    lease_token = NULL,
    last_error = NULL
WHERE id = ? AND status = 'processing' AND lease_token = ?
"""

RETRY_SQL = """
UPDATE outbox_events
SET status = ?,
    available_at = ?,
    lease_until = NULL,
    lease_token = NULL,
    last_error = ?
WHERE id = ? AND status = 'processing' AND lease_token = ?
"""


def _utc(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Outbox timestamps must be timezone-aware.")
    return result.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def claim_next(
    db: D1Database,
    *,
    now: datetime | None = None,
    lease_seconds: int = 60,
) -> dict[str, Any] | None:
    if not isinstance(lease_seconds, int) or not 5 <= lease_seconds <= 900:
        raise ValueError("Outbox lease must be between 5 and 900 seconds.")
    instant = _utc(now)
    stamp = _stamp(instant)
    lease_until = _stamp(instant + timedelta(seconds=lease_seconds))
    lease_token = str(uuid4())
    return await db.first(CLAIM_SQL, (lease_until, lease_token, stamp, stamp))


async def mark_delivered(
    db: D1Database, event_id: str, lease_token: str, *, now: datetime | None = None
) -> None:
    if not event_id or len(event_id) > 255 or not lease_token or len(lease_token) > 64:
        raise ValueError("Invalid outbox delivery lease.")
    await db.execute(DELIVER_SQL, (_stamp(_utc(now)), event_id, lease_token))


async def mark_retry(
    db: D1Database,
    event: dict[str, Any],
    *,
    retryable: bool = True,
    now: datetime | None = None,
) -> str:
    event_id = event.get("id")
    attempts = event.get("attempts")
    max_attempts = event.get("max_attempts")
    lease_token = event.get("lease_token")
    if (
        not isinstance(event_id, str) or not event_id or len(event_id) > 255
        or type(attempts) is not int or attempts < 1
        or type(max_attempts) is not int or not 1 <= max_attempts <= 20
        or not isinstance(lease_token, str) or not lease_token or len(lease_token) > 64
    ):
        raise ValueError("Invalid claimed outbox event.")
    instant = _utc(now)
    terminal = (not retryable) or attempts >= max_attempts
    delay = min(3600, 30 * (2 ** min(attempts - 1, 7)))
    status = "dead" if terminal else "pending"
    await db.execute(
        RETRY_SQL,
        (
            status,
            _stamp(instant + timedelta(seconds=delay)),
            "delivery_failed",
            event_id,
            lease_token,
        ),
    )
    return status


async def dispatch_one(
    db: D1Database,
    publish_event_id: Callable[[str], Awaitable[Any] | Any],
    *,
    now: datetime | None = None,
    lease_seconds: int = 60,
) -> str:
    """Publish one event ID; returns idle, delivered, retry, or dead."""
    instant = _utc(now)
    event = await claim_next(db, now=instant, lease_seconds=lease_seconds)
    if event is None:
        return "idle"

    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise OutboxError("Claimed outbox event has no valid ID.")

    try:
        result = publish_event_id(event_id)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:
        return await mark_retry(db, event, retryable=_is_retryable(exc), now=instant)

    lease_token = event.get("lease_token")
    if not isinstance(lease_token, str) or not lease_token:
        raise OutboxError("Claimed outbox event has no valid lease token.")
    await mark_delivered(db, event_id, lease_token, now=instant)
    return "delivered"
