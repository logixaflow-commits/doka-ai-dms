import pytest

from app.services.train1_safety_contracts import (
    CircuitBreaker,
    CircuitState,
    ContractViolation,
    ConsentGrant,
    ErrorClass,
    RetrievalDocument,
    SchemaField,
    classify_error,
    decide_retry,
    select_failover_provider,
    make_dlq_record,
    require_consent,
    require_human_approval,
    validate_output_schema,
    validate_retrieval_documents,
)


class RetryableError(Exception):
    retryable = True


class NonRetryableError(Exception):
    retryable = False


def test_error_taxonomy_is_conservative():
    assert classify_error(RetryableError()) is ErrorClass.RETRYABLE
    assert classify_error(NonRetryableError()) is ErrorClass.NON_RETRYABLE
    assert classify_error(ValueError("unknown")) is ErrorClass.NON_RETRYABLE


def test_retry_exhaustion_and_non_retryable_boundary():
    retry = decide_retry(RetryableError(), 1, 3)
    assert retry.should_retry and not retry.exhausted
    exhausted = decide_retry(RetryableError(), 3, 3)
    assert exhausted.exhausted and not exhausted.should_retry
    permanent = decide_retry(NonRetryableError(), 1, 3)
    assert permanent.exhausted and not permanent.should_retry


def test_dlq_requires_complete_identity():
    assert make_dlq_record("job-1", "key-1", "retry budget exhausted", 3).attempts == 3
    with pytest.raises(ContractViolation):
        make_dlq_record("", "key-1", "reason", 1)


def test_circuit_breaker_closed_open_half_open_and_recovery():
    breaker = CircuitBreaker(failure_threshold=2, recovery_after=10)
    assert breaker.allow(0)
    breaker.failure(0)
    breaker.failure(1)
    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow(5)
    assert breaker.allow(11)
    assert breaker.state is CircuitState.HALF_OPEN
    breaker.success()
    assert breaker.state is CircuitState.CLOSED


def test_half_open_failure_reopens():
    breaker = CircuitBreaker(failure_threshold=1, recovery_after=10)
    breaker.failure(0)
    assert breaker.state is CircuitState.OPEN
    assert breaker.allow(10)
    breaker.failure(10)
    assert breaker.state is CircuitState.OPEN


def test_consent_is_exact_and_fail_closed():
    grant = ConsentGrant("user-1", "summarize", "document:7", True)
    require_consent(grant, subject_id="user-1", purpose="summarize", scope="document:7")
    with pytest.raises(ContractViolation):
        require_consent(grant, subject_id="user-1", purpose="export", scope="document:7")
    with pytest.raises(ContractViolation):
        require_consent(None, subject_id="user-1", purpose="summarize", scope="document:7")


def test_schema_validation_is_fail_closed():
    fields = (SchemaField("answer"), SchemaField("citations", required=False))
    assert validate_output_schema({"answer": "ok"}, fields)["answer"] == "ok"
    with pytest.raises(ContractViolation):
        validate_output_schema({}, fields)
    with pytest.raises(ContractViolation):
        validate_output_schema({"answer": "ok", "unsafe": True}, fields)


def test_multilingual_retrieval_contract_requires_identity_hash_and_language():
    docs = [RetrievalDocument("7", "mya", "abc"), RetrievalDocument("8", "eng", "def")]
    assert len(validate_retrieval_documents(docs)) == 2
    with pytest.raises(ContractViolation):
        validate_retrieval_documents([RetrievalDocument("9", "fra", "ghi")])


def test_human_approval_is_required_for_side_effects():
    require_human_approval(True, side_effect=True, approver_id="admin-1")
    require_human_approval(False, side_effect=False)
    with pytest.raises(ContractViolation):
        require_human_approval(True, side_effect=True)
    with pytest.raises(ContractViolation):
        require_human_approval(False, side_effect=True, approver_id="admin-1")

def test_failover_requires_explicit_approval_and_healthy_alternate():
    assert select_failover_provider(
        ["primary", "secondary"], {"primary"},
        original_provider="primary", approved_for_failover=True,
    ) == "secondary"
    with pytest.raises(ContractViolation):
        select_failover_provider(
            ["primary", "secondary"], {"primary"},
            original_provider="primary", approved_for_failover=False,
        )
    with pytest.raises(ContractViolation):
        select_failover_provider(
            ["primary", "secondary"], {"primary", "secondary"},
            original_provider="primary", approved_for_failover=True,
        )


def test_half_open_allows_only_one_recovery_probe():
    breaker = CircuitBreaker(failure_threshold=1, recovery_after=10)
    breaker.failure(0)

    assert breaker.allow(10)
    assert breaker.state is CircuitState.HALF_OPEN
    assert not breaker.allow(10)
    assert not breaker.allow(11)

    breaker.success(probe=True)
    assert breaker.state is CircuitState.CLOSED
    assert breaker.allow(12)


def test_stale_completion_cannot_corrupt_open_circuit():
    breaker = CircuitBreaker(failure_threshold=1, recovery_after=10)
    assert breaker.allow(0)  # request A admitted while closed
    breaker.failure(1, probe=False)  # request B opens the circuit
    assert breaker.state is CircuitState.OPEN

    breaker.success(probe=False)  # stale success from request A
    assert breaker.state is CircuitState.OPEN
    assert breaker.opened_at == 1
    assert not breaker.allow(5)


def test_cancelled_half_open_probe_reopens_with_new_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, recovery_after=10)
    breaker.failure(0)
    assert breaker.allow(10)

    breaker.abandon_probe(12)
    assert breaker.state is CircuitState.OPEN
    assert breaker.opened_at == 12
    assert not breaker.allow(21)
    assert breaker.allow(22)
