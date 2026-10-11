# AI external-processing consent lifecycle

The Personal Local runtime exposes an authenticated, database-backed consent lifecycle. A consent record is bound to the authenticated local subject, a supported processing purpose, and an explicit resource scope. A caller-supplied `ConsentGrant` object is not accepted as evidence: the AI service reads the current active grant from the local SQLite auth-state database before every external operation.

## API

All endpoints require the current local bearer access token.

- `GET /api/ai/consent` — list the authenticated subject's grants and revocation state.
- `PUT /api/ai/consent` — grant or revoke consent. JSON body: `{"purpose":"document_analysis","scope":"document:123","granted":true}`.
- `GET /api/ai/consent/audit?limit=100` — list this subject's consent audit events (maximum 500).

Supported purposes are `document_analysis`, `embedding`, and `duplicate_detection`. Scope is explicit and limited to 512 characters; use a stable resource identifier such as `document:<id>` or an approved workspace identifier. The API derives subject and actor from the verified access token; clients cannot select another subject. Request IDs are captured in the audit trail.

## Persistence and revocation

Consent grant state is stored in `LOCAL_AUTH_STATE_PATH`, alongside local session state. The file is created with restrictive POSIX permissions where supported and is rejected if it is a symlink or resides inside the protected source/working roots. Grant changes are transactional. Revocation marks the grant inactive instead of deleting its history. Audit events are append-only at the SQLite schema level and record grant/revoke action, subject, actor, purpose, scope, timestamp, and request ID.

The AI service re-reads persisted consent at the external-processing boundary, so revocation blocks subsequent calls without waiting for a cache expiry. Missing, mismatched, revoked, or unreadable consent state fails closed. Local/rule-based processing remains available. The separate `AI_ENABLED=true` and `AI_EXTERNAL_PROCESSING_CONSENT=true` deployment gates must also be enabled before external providers can receive data.

## Caller contract

Internal AI callers must propagate the verified subject ID and an explicit scope obtained from the authenticated request context. Document authorization remains a separate check: a consent scope is not proof that the caller may read the referenced document. If identity or scope is unavailable, the AI detector uses local-only behavior or returns no external classification.

## Verification

Regression coverage is in `web-platform/backend/tests/test_consent_store.py` and `web-platform/backend/tests/test_ai_provider_boundaries.py`. It covers exact subject/purpose/scope matching, persisted grant lookup, revocation, retained audit history, and ignoring forged in-memory grant objects.
