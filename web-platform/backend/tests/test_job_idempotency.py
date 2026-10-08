import concurrent.futures
from pathlib import Path

import pytest

from app.services.job_idempotency import JobIdempotencyStore


def test_duplicate_claim_reuses_durable_record(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)
    first, created = store.claim("job-1", "job-key")
    second, duplicate = store.claim("job-1", "job-key")

    assert created is True
    assert duplicate is False
    assert second == first
    assert store.get("job-key").status == "received"


def test_same_key_cannot_bind_two_jobs(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)
    store.claim("job-1", "job-key")

    with pytest.raises(ValueError, match="another job"):
        store.claim("job-2", "job-key")


def test_retry_exhaustion_and_dlq_transition(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)
    store.claim("job-1", "job-key", max_attempts=2)

    store.start("job-key")
    retryable = store.fail("job-key", "temporary failure", retryable=True)
    assert retryable.status == "retryable"
    assert retryable.attempt == 1

    store.start("job-key")
    exhausted = store.fail("job-key", "second failure", retryable=True)
    assert exhausted.status == "exhausted"
    assert exhausted.attempt == 2

    dlq = store.dead_letter("job-key", "retry budget exhausted")
    assert dlq.status == "dead_lettered"
    assert store.get("job-key").status == "dead_lettered"


def test_terminal_success_is_replay_safe(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)
    store.claim("job-1", "job-key")
    store.start("job-key")
    first = store.succeed("job-key", {"document_id": 7})
    second = store.succeed("job-key", {"document_id": 8})

    assert first.status == "succeeded"
    assert second.result == {"document_id": 7}


def test_concurrent_duplicate_claim_only_creates_one_record(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)

    def claim():
        return store.claim("job-1", "shared-key")[1]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        created = list(pool.map(lambda _: claim(), range(8)))

    assert sum(created) == 1
    assert store.get("shared-key").job_id == "job-1"


def test_takeover_is_not_part_of_this_contract(tmp_path: Path):
    store = JobIdempotencyStore(tmp_path)
    store.claim("job-1", "job-key")

    assert not hasattr(store, "take_over")
    assert not hasattr(store, "lease")
    assert not hasattr(store, "ack_late")
