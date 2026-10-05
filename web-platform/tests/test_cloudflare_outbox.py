"""Tests for leased outbox delivery and retry boundaries."""
import asyncio
from datetime import datetime, timezone

import pytest

from cloudflare_worker.outbox import (
    CLAIM_SQL, DELIVER_SQL, RETRY_SQL, OutboxError, claim_next,
    dispatch_one, mark_retry,
)


class FakeD1:
    def __init__(self, event=None):
        self.event = event
        self.calls = []

    async def first(self, sql, parameters=()):
        self.calls.append(("first", sql, parameters))
        return self.event

    async def execute(self, sql, parameters=()):
        self.calls.append(("execute", sql, parameters))
        return {"success": True, "meta": {"changes": 1}}


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def test_claim_uses_lease_and_recovers_expired_processing_events():
    db = FakeD1({"id": "evt-1", "lease_token": "token-1"})
    assert asyncio.run(claim_next(db, now=NOW, lease_seconds=60)) == {"id": "evt-1"}
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


def test_dispatch_failure_does_not_leak_exception_and_schedules_retry():
    db = FakeD1({"id": "evt-5", "attempts": 1, "max_attempts": 3, "lease_token": "token-5"})

    def fail(_event_id):
        raise RuntimeError("secret URL and credentials")

    assert asyncio.run(dispatch_one(db, fail, now=NOW)) == "pending"
    assert db.calls[-1][1] == RETRY_SQL
    assert "secret URL" not in str(db.calls[-1])


def test_dispatch_idle_when_no_pending_event():
    assert asyncio.run(dispatch_one(FakeD1(), lambda _event_id: None, now=NOW)) == "idle"
