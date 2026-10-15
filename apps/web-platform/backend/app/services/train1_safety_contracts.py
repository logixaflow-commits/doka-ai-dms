"""Train 1 safety contracts.

Transport/provider agnostic contracts used to constrain future queue and AI
integrations. These contracts fail closed and deliberately do not perform
network calls or enable worker takeover.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional

try:
    import httpx
except ImportError:  # pragma: no cover - optional at contract-only runtime
    httpx = None


class ErrorClass(str, Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"


class JobStatus(str, Enum):
    RUNNING = "running"
    RETRYABLE = "retryable"
    EXHAUSTED = "exhausted"
    DEAD_LETTERED = "dead_lettered"
    SUCCEEDED = "succeeded"


class ContractViolation(ValueError):
    pass


def classify_error(error: BaseException) -> ErrorClass:
    """Conservative taxonomy: unknown errors are non-retryable."""
    explicit = getattr(error, "retryable", None)
    if explicit is True:
        return ErrorClass.RETRYABLE
    if explicit is False:
        return ErrorClass.NON_RETRYABLE
    if isinstance(error, (TimeoutError, ConnectionError)):
        return ErrorClass.RETRYABLE
    return ErrorClass.NON_RETRYABLE


@dataclass(frozen=True)
class RetryDecision:
    error_class: ErrorClass
    should_retry: bool
    exhausted: bool
    next_attempt: int


def decide_retry(error: BaseException, attempt: int, max_attempts: int) -> RetryDecision:
    if attempt < 1 or max_attempts < 1 or attempt > max_attempts:
        raise ContractViolation("Invalid retry attempt bounds")
    error_class = classify_error(error)
    should_retry = error_class is ErrorClass.RETRYABLE and attempt < max_attempts
    return RetryDecision(
        error_class=error_class,
        should_retry=should_retry,
        exhausted=not should_retry,
        next_attempt=attempt + 1,
    )


@dataclass(frozen=True)
class DlqRecord:
    job_id: str
    idempotency_key: str
    reason: str
    attempts: int


def make_dlq_record(job_id: str, idempotency_key: str, reason: str, attempts: int) -> DlqRecord:
    if not job_id or not idempotency_key or not reason or attempts < 1:
        raise ContractViolation("Incomplete DLQ record")
    return DlqRecord(job_id, idempotency_key, reason, attempts)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Deterministic breaker; caller supplies the clock."""

    def __init__(self, failure_threshold: int = 3, recovery_after: float = 30.0):
        if failure_threshold < 1 or recovery_after <= 0:
            raise ContractViolation("Invalid circuit breaker limits")
        self.failure_threshold = failure_threshold
        self.recovery_after = recovery_after
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at: Optional[float] = None
        self._probe_in_flight = False

    def allow(self, now: float) -> bool:
        if self.state is CircuitState.CLOSED:
            return True
        if self.state is CircuitState.OPEN and self.opened_at is not None:
            if now - self.opened_at >= self.recovery_after:
                self.state = CircuitState.HALF_OPEN
                self._probe_in_flight = True
                return True
        # Exactly one recovery probe may be in flight per process. This is a
        # local concurrency guard, not a distributed circuit registry.
        return False

    def success(self, *, probe: Optional[bool] = None) -> None:
        # Ignore stale completions from requests admitted before the circuit
        # opened; they must not erase the cooldown or close an open circuit.
        is_probe = self.state is CircuitState.HALF_OPEN if probe is None else probe
        if self.state is CircuitState.HALF_OPEN:
            if not is_probe:
                return
            self.state = CircuitState.CLOSED
            self._probe_in_flight = False
            self.failures = 0
            self.opened_at = None
            return
        if self.state is CircuitState.CLOSED:
            self.failures = 0
            self.opened_at = None

    def failure(self, now: float, *, probe: Optional[bool] = None) -> None:
        is_probe = self.state is CircuitState.HALF_OPEN if probe is None else probe
        if self.state is CircuitState.HALF_OPEN:
            if not is_probe:
                return
            self.state = CircuitState.OPEN
            self._probe_in_flight = False
            self.opened_at = now
            return
        if self.state is CircuitState.OPEN:
            # A stale request finishing after another request opened the
            # circuit must not extend or otherwise corrupt the open interval.
            return
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = now

    def abandon_probe(self, now: float) -> None:
        """Re-open after a cancelled recovery probe; never leave it stuck half-open."""
        if self.state is CircuitState.HALF_OPEN and self._probe_in_flight:
            self.state = CircuitState.OPEN
            self._probe_in_flight = False
            self.opened_at = now


def select_failover_provider(
    providers: list[str],
    unavailable: set[str],
    *,
    original_provider: str,
    approved_for_failover: bool,
) -> str:
    """Select a deterministic alternate only when failover is explicitly allowed."""
    if not providers or original_provider not in providers:
        raise ContractViolation("Original provider is not configured")
    if not approved_for_failover:
        raise ContractViolation("Provider failover requires explicit approval")
    for provider in providers:
        if provider != original_provider and provider not in unavailable:
            return provider
    raise ContractViolation("No safe failover provider available")


@dataclass(frozen=True)
class ConsentGrant:
    subject_id: str
    purpose: str
    scope: str
    granted: bool


def require_consent(grant: Optional[ConsentGrant], *, subject_id: str, purpose: str, scope: str) -> None:
    if grant is None or not grant.granted:
        raise ContractViolation("Consent required")
    if (grant.subject_id, grant.purpose, grant.scope) != (subject_id, purpose, scope):
        raise ContractViolation("Consent scope mismatch")


@dataclass(frozen=True)
class SchemaField:
    name: str
    required: bool = True


def validate_output_schema(value: Any, fields: tuple[SchemaField, ...]) -> Mapping[str, Any]:
    """Fail closed: object type, required keys, and no unknown keys."""
    if not isinstance(value, dict):
        raise ContractViolation("AI output must be an object")
    names = {field.name for field in fields}
    unknown = set(value) - names
    missing = {field.name for field in fields if field.required and field.name not in value}
    if unknown or missing:
        raise ContractViolation("AI output schema mismatch")
    return value


@dataclass(frozen=True)
class RetrievalDocument:
    document_id: str
    language: str
    text_hash: str


def validate_retrieval_documents(
    documents: list[RetrievalDocument],
    *,
    allowed_languages: frozenset[str] = frozenset({"mya", "eng"}),
) -> tuple[RetrievalDocument, ...]:
    if not isinstance(documents, list):
        raise ContractViolation("Retrieval result must be a list")
    if any(not d.document_id or not d.text_hash for d in documents):
        raise ContractViolation("Retrieval document identity/hash required")
    if any(d.language not in allowed_languages for d in documents):
        raise ContractViolation("Unsupported retrieval language")
    return tuple(documents)


def require_human_approval(
    approved: bool,
    *,
    side_effect: bool,
    approver_id: Optional[str] = None,
) -> None:
    if side_effect and (not approved or not approver_id):
        raise ContractViolation("Human approval required for side effect")
