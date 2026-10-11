"""Contract tests for the durable D1 job ledger."""
import asyncio
from datetime import datetime, timezone

import pytest

from cloudflare_worker.jobs import (
    CLAIM_SQL,
    CREATE_SQL,
    FAIL_SQL,
    SUCCEED_SQL,
    JobStateConflict,
    claim_next_job,
    create_or_get_job,
    mark_failed,
    mark_succeeded,
    payload_digest,
)

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


class FakeD1:
    def __init__(self, rows=None, *, changes=1):
        self.rows = list(rows or [])
        self.changes = changes
        self.calls = []

    async def execute(self, sql, parameters=()):
        self.calls.append(("execute", sql, parameters))
        return {"success": True, "meta": {"changes": self.changes}}

    async def first(self, sql, parameters=()):
        self.calls.append(("first", sql, parameters))
        if sql == CLAIM_SQL:
            return self.rows[0] if self.rows else None
        return self.rows[0] if self.rows else None


def test_create_or_get_is_idempotent_and_binds_payload():
    db = FakeD1([{
        "id": "job-1",
        "job_type": "ocr",
        "idempotency_key": "doc-1:ocr",
        "payload_json": '{"document_id":"doc-1"}',
    }])
    row = asyncio.run(create_or_get_job(
        db,
        job_id="job-1",
        job_type="ocr",
        idempotency_key="doc-1:ocr",
        payload={"document_id": "doc-1"},
        max_attempts=5,
    ))
    assert row["id"] == "job-1"
    assert db.calls[0][1] == CREATE_SQL
    assert payload_digest(row["payload_json"]) == payload_digest('{"document_id":"doc-1"}')


def test_create_or_get_rejects_key_reuse_for_different_payload():
    db = FakeD1([{
        "id": "job-1",
        "job_type": "ocr",
        "idempotency_key": "doc-1:ocr",
        "payload_json": '{"document_id":"doc-1"}',
    }])
    with pytest.raises(ValueError, match="different payload"):
        asyncio.run(create_or_get_job(
            db,
            job_id="job-2",
            job_type="ocr",
            idempotency_key="doc-1:ocr",
            payload={"document_id": "doc-2"},
        ))


def test_claim_uses_durable_pending_state_without_takeover():
    db = FakeD1([{
        "id": "job-2",
        "status": "processing",
        "attempts": 1,
        "max_attempts": 5,
        "idempotency_key": "job-2",
    }])
    row = asyncio.run(claim_next_job(db, now=NOW))
    assert row["id"] == "job-2"
    assert db.calls[0][1] == CLAIM_SQL
    assert db.calls[0][2] == ("2026-10-08T12:00:00.000Z",) * 2


def test_retryable_failure_returns_pending_with_bounded_backoff():
    db = FakeD1()
    job = {"id": "job-3", "attempts": 2, "max_attempts": 5}
    assert asyncio.run(mark_failed(db, job, retryable=True, error="temporary", now=NOW)) == "pending"
    assert db.calls[0][1] == FAIL_SQL
    assert db.calls[0][2][0] == "pending"
    assert db.calls[0][2][1] == "2026-10-08T12:01:00.000Z"


def test_non_retryable_and_exhausted_failures_are_dead():
    db = FakeD1()
    assert asyncio.run(mark_failed(
        db, {"id": "job-4", "attempts": 1, "max_attempts": 5},
        retryable=False, error="schema-invalid", now=NOW,
    )) == "dead"
    assert asyncio.run(mark_failed(
        db, {"id": "job-5", "attempts": 5, "max_attempts": 5},
        retryable=True, error="timeout", now=NOW,
    )) == "dead"


def test_success_writes_terminal_result():
    db = FakeD1()
    asyncio.run(mark_succeeded(db, {"id": "job-6"}, {"ok": True}, now=NOW))
    assert db.calls[0][1] == SUCCEED_SQL
    assert db.calls[0][2][0] == '{"ok":true}'


@pytest.mark.parametrize("key", ["", "bad key", "a" * 256])
def test_invalid_idempotency_key_is_rejected(key):
    with pytest.raises(ValueError):
        asyncio.run(create_or_get_job(
            FakeD1(), job_id="job", job_type="ocr", idempotency_key=key, payload={},
        ))


def test_success_rejects_stale_job_state_transition():
    db = FakeD1(changes=0)
    with pytest.raises(JobStateConflict, match="expected job state"):
        asyncio.run(mark_succeeded(db, {"id": "job-stale"}, {"ok": True}, now=NOW))


def test_failure_rejects_stale_job_state_transition():
    db = FakeD1(changes=0)
    with pytest.raises(JobStateConflict, match="expected job state"):
        asyncio.run(mark_failed(
            db,
            {"id": "job-stale", "attempts": 1, "max_attempts": 3},
            retryable=True,
            error="temporary",
            now=NOW,
        ))
