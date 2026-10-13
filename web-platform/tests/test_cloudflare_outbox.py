"""Tests for leased outbox delivery and retry boundaries."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from cloudflare_worker.outbox import (
    CLAIM_SQL, DELIVER_SQL, RETRY_SQL, OutboxError, claim_next,
    dispatch_one, mark_delivered, mark_retry, _is_retryable,
)


class FakeD1:
    def __init__(self, event=None, *, changes=1):
        self.event = event
        self.changes = changes
        self.calls = []

    async def first(self, sql, parameters=()):
        self.calls.append(("first", sql, parameters))
        return self.event

    async def execute(self, sql, parameters=()):
        self.calls.append(("execute", sql, parameters))
        return {"success": True, "meta": {"changes": self.changes}}


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def test_claim_uses_lease_and_recovers_expired_processing_events():
    db = FakeD1({"id": "evt-1", "lease_token": "token-1"})
    assert asyncio.run(claim_next(db, now=NOW, lease_seconds=60)) == {"id": "evt-1", "lease_token": "token-1"}
    kind, sql, params = db.calls[0]
    assert kind == "first"
    assert "status = 'processing'" in sql
    assert "lease_until <= ?" in sql
    assert params[0] == "2026-10-05T12:01:00.000Z"
    assert params[1] == "token-1" or len(params[1]) == 36


@pytest.mark.parametrize("lease", [0, 4, 901, True])
def test_claim_rejects_invalid_lease(lease):
    with pytest.raises(ValueError):
        asyncio.run(claim_next(FakeD1(), now=NOW, lease_seconds=lease))


def test_claim_rejects_naive_clock():
    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(claim_next(FakeD1(), now=datetime(2026, 10, 5, 12, 0)))


def test_failed_delivery_retries_with_bounded_backoff_and_safe_error():
    db = FakeD1()
    event = {"id": "evt-2", "attempts": 2, "max_attempts": 5, "lease_token": "token-2"}
    result = asyncio.run(mark_retry(db, event, now=NOW))
    assert result == "pending"
    _, sql, params = db.calls[0]
    assert sql == RETRY_SQL
    assert params == (
        "pending", "2026-10-05T12:01:00.000Z", "delivery_failed", "evt-2", "token-2"
    )


def test_retry_moves_exhausted_event_to_dead_letter_state():
    db = FakeD1()
    event = {"id": "evt-3", "attempts": 5, "max_attempts": 5, "lease_token": "token-3"}
    assert asyncio.run(mark_retry(db, event, now=NOW)) == "dead"
    assert db.calls[0][2][0] == "dead"


def test_retry_rejects_malformed_event():
    with pytest.raises(ValueError):
        asyncio.run(mark_retry(FakeD1(), {"id": "evt", "attempts": 0, "max_attempts": 5, "lease_token": "t"}, now=NOW))


def test_dispatch_publishes_only_event_id_then_marks_delivered():
    db = FakeD1({
        "id": "evt-4", "event_type": "document.updated",
        "aggregate_type": "document", "aggregate_id": "doc-1",
        "attempts": 1, "max_attempts": 8, "lease_token": "token-4",
    })
    published = []

    async def publish(event_id):
        published.append(event_id)

    assert asyncio.run(dispatch_one(db, publish, now=NOW)) == "delivered"
    assert published == ["evt-4"]
    assert db.calls[1][1] == DELIVER_SQL
    assert db.calls[1][2][1] == "evt-4"
    assert db.calls[1][2][2] == "token-4"


def test_non_retryable_dispatch_failure_moves_event_to_dead():
    db = FakeD1({"id": "evt-schema", "attempts": 1, "max_attempts": 3, "lease_token": "token-schema"})

    class PermanentError(Exception):
        retryable = False

    def fail(_event_id):
        raise PermanentError("schema invalid")

    assert asyncio.run(dispatch_one(db, fail, now=NOW)) == "dead"
    assert db.calls[-1][2][0] == "dead"


def test_dispatch_failure_does_not_leak_exception_and_schedules_retry():
    db = FakeD1({"id": "evt-5", "attempts": 1, "max_attempts": 3, "lease_token": "token-5"})

    def fail(_event_id):
        raise TimeoutError("temporary delivery failure")

    assert asyncio.run(dispatch_one(db, fail, now=NOW)) == "pending"
    assert db.calls[-1][1] == RETRY_SQL
    assert "secret URL" not in str(db.calls[-1])


def test_dispatch_idle_when_no_pending_event():
    assert asyncio.run(dispatch_one(FakeD1(), lambda _event_id: None, now=NOW)) == "idle"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (408, True),
        (425, True),
        (429, True),
        (500, True),
        (599, True),
        (400, False),
        (401, False),
        (404, False),
        (600, False),
        ("503", False),
        (None, False),
    ],
)
def test_retry_classification_is_type_safe_and_fail_closed(status, expected):
    error = RuntimeError("provider failure")
    error.response = SimpleNamespace(status_code=status)
    assert _is_retryable(error) is expected


def test_delivery_rejects_stale_lease_state_transition():
    db = FakeD1(changes=0)
    with pytest.raises(OutboxError, match="expected outbox state"):
        asyncio.run(mark_delivered(db, "evt-stale", "lease-stale", now=NOW))


def test_retry_rejects_stale_lease_state_transition():
    db = FakeD1(changes=0)
    event = {"id": "evt-stale", "attempts": 1, "max_attempts": 3, "lease_token": "lease-stale"}
    with pytest.raises(OutboxError, match="expected outbox state"):
        asyncio.run(mark_retry(db, event, now=NOW))


class SQLiteD1:
    """Exercise the production outbox SQL against SQLite's atomic UPDATE/RETURNING."""

    def __init__(self):
        import sqlite3

        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE outbox_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 8,
                available_at TEXT NOT NULL,
                lease_until TEXT,
                lease_token TEXT,
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                last_error TEXT
            )
        """)
        self.connection.commit()

    async def first(self, sql, parameters=()):
        cursor = self.connection.execute(sql, tuple(parameters))
        row = cursor.fetchone()
        self.connection.commit()
        return dict(row) if row is not None else None

    async def execute(self, sql, parameters=()):
        cursor = self.connection.execute(sql, tuple(parameters))
        self.connection.commit()
        return {"success": True, "meta": {"changes": cursor.rowcount}}

    def insert_event(self, event_id, *, status="pending", lease_until=None, attempts=0, created_at=None):
        stamp = created_at or "2026-10-05T11:00:00.000Z"
        self.connection.execute(
            """INSERT INTO outbox_events
               (id, event_type, aggregate_type, aggregate_id, idempotency_key,
                payload_json, status, attempts, max_attempts, available_at,
                lease_until, created_at)
               VALUES (?, 'document.updated', 'document', 'doc-1', ?,
                       '{}', ?, ?, 3, '2026-10-05T11:00:00.000Z', ?, ?)""",
            (event_id, f"idem-{event_id}", status, attempts, lease_until, stamp),
        )
        self.connection.commit()


def test_sqlite_claim_is_exclusive_and_stale_lease_cannot_acknowledge():
    db = SQLiteD1()
    db.insert_event("evt-a", created_at="2026-10-05T11:00:00.000Z")
    db.insert_event("evt-b", created_at="2026-10-05T11:01:00.000Z")

    first = asyncio.run(claim_next(db, now=NOW, lease_seconds=60))
    second = asyncio.run(claim_next(db, now=NOW, lease_seconds=60))
    assert first is not None and second is not None
    assert first["id"] != second["id"]

    # A lease reclaimed after expiry gets a fresh token; the old worker cannot
    # mark the event delivered after ownership has moved to the new worker.
    old_token = first["lease_token"]
    db.connection.execute(
        "UPDATE outbox_events SET lease_until = ? WHERE id = ?",
        ("2026-10-05T11:59:59.000Z", first["id"]),
    )
    db.connection.commit()
    reclaimed = asyncio.run(claim_next(db, now=NOW, lease_seconds=60))
    assert reclaimed is not None and reclaimed["id"] == first["id"]
    assert reclaimed["lease_token"] != old_token
    with pytest.raises(OutboxError, match="expected outbox state"):
        asyncio.run(mark_delivered(db, first["id"], old_token, now=NOW))
    asyncio.run(mark_delivered(db, reclaimed["id"], reclaimed["lease_token"], now=NOW))


def test_sqlite_retry_exhaustion_persists_dead_letter_state():
    db = SQLiteD1()
    db.insert_event("evt-dead", attempts=2)
    claimed = asyncio.run(claim_next(db, now=NOW, lease_seconds=60))
    assert claimed is not None
    # max_attempts is three, and claim increments attempts from two to three.
    assert claimed["attempts"] == 3
    status = asyncio.run(mark_retry(db, claimed, retryable=True, now=NOW))
    assert status == "dead"
    row = db.connection.execute(
        "SELECT status, lease_token, lease_until, last_error FROM outbox_events WHERE id = ?",
        ("evt-dead",),
    ).fetchone()
    assert tuple(row) == ("dead", None, None, "delivery_failed")


@pytest.mark.parametrize("retryable", [None, 0, 1, "false", [], {}])
def test_mark_retry_rejects_non_boolean_retry_classification(retryable):
    with pytest.raises(ValueError, match="retryable must be a boolean"):
        asyncio.run(mark_retry(
            FakeD1(), {"id": "evt-invalid-retry", "attempts": 1, "max_attempts": 3, "lease_token": "lease"},
            retryable=retryable, now=NOW,
        ))


@pytest.mark.parametrize(("event_id", "lease_token"), [(1, "lease"), ("evt", 7), ("", "lease"), ("evt", "")])
def test_mark_delivered_rejects_malformed_lease_identifiers(event_id, lease_token):
    with pytest.raises(ValueError, match="Invalid outbox delivery lease"):
        asyncio.run(mark_delivered(FakeD1(), event_id, lease_token, now=NOW))


def test_claim_rejects_boolean_lease_duration():
    with pytest.raises(ValueError, match="between 5 and 900"):
        asyncio.run(claim_next(FakeD1(), now=NOW, lease_seconds=True))
