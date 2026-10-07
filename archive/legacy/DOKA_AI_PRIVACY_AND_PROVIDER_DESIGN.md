# Doka AI Privacy, Provider & Human-Review Design

Status: AI remains off by default. A separate explicit external-processing consent gate is implemented in the Personal Local AI orchestration path.

## Default behavior

- `AI_ENABLED=false` by default.
- `AI_EXTERNAL_PROCESSING_CONSENT=false` by default.
- External provider calls are blocked unless both flags are true.
- Deterministic rules, local parsing and local OCR remain available without AI.
- Provider API keys are server-side only and must never enter browser bundles, document metadata or logs.

## Data flow

Before enabling an external provider, the application must identify the minimum text/metadata required for the operation, disclose the provider and purpose, and obtain the user's explicit consent. Do not send entire documents by default. Prefer local extraction followed by a minimal, redacted excerpt.

## Provider adapter contract

Every provider adapter should implement:
- provider/model identity and capability declaration;
- request timeout and bounded retry policy;
- normalized structured output with schema validation;
- explicit token/input limits and estimated cost;
- safe error classification without returning raw provider payloads to users;
- cancellation and provider-disable handling.

Provider order is configuration, not a hard dependency. A provider failure must fall back to deterministic/local processing where possible; it must never silently bypass the consent gate.

## Human approval and safety

AI may suggest classification, tags, metadata, duplicates or folder destinations. It must not:
- mutate originals;
- move, rename, delete or share documents without explicit human approval;
- change permissions or role membership;
- follow instructions embedded inside untrusted document text;
- mark its own output as verified without provenance.

Persist provider, model, timestamp, operation, confidence, schema version and a safe provenance reference. Do not persist full prompts or document contents in ordinary logs.

## Privacy and operational controls

- Provide per-user/org opt-in and a clear off switch.
- Redact secrets and sensitive identifiers before provider calls where feasible.
- Enforce rate limits, request-size limits, concurrency caps and spend visibility.
- Keep provider secrets server-side; rotate and revoke them safely.
- Maintain a provider evaluation set with Myanmar and English examples.
- Measure extraction accuracy, false classifications, hallucination rate and reviewer correction rate.
- Document provider retention/training settings from current provider terms before production use; do not make blanket retention guarantees.

## Implemented baseline

- `UnifiedAIService` is provider-neutral and has ordered fallback.
- `AI_ENABLED` defaults to false.
- `AI_EXTERNAL_PROCESSING_CONSENT` defaults to false and is independently required before external provider calls.
- A regression test confirms no provider is called without consent.

## Activation gate

AI remains unavailable in production UI until consent UX, redaction, schema validation, human review, evaluation results, quota controls and a security/privacy review are complete.
