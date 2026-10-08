# Doka Phase 7–18 Execution Plan

This plan turns the post-release roadmap into executable feature trains. A phase
does not become DONE merely because code exists. Each train follows:

**contract → implementation → feature flag → migration → rollback path → security review → performance baseline → acceptance evidence → activation**

## Phase 7/8 — Workflow + AI Hardening

### Objectives
- Durable workflow execution with explicit state transitions, idempotency and retry boundaries.
- Provider quality/cost routing with circuit breaking and bounded attempts.
- Multilingual retrieval and OCR-aware ranking.
- AI safety: consent, input/output limits, schema validation and human approval.

### Current foundation
- AI provider fallback/circuit breaker and schema validation exist; live provider activation remains evidence-gated.
- Organization planning is review-only by default.
- Workflow engine now rejects empty/invalid step definitions and rejects stale/wrong-step completion.
- Workflow completion now accepts a bounded idempotency key, serializes per-instance transitions, writes instances with atomic replacement/fsync, and returns an idempotent result for duplicate delivery. A new transport-agnostic durable job idempotency contract also records claim/status/attempt/result state with atomic replacement and replay-safe terminal outcomes; its contract tests cover retry exhaustion, DLQ transition and concurrent duplicate claims.

### Safety boundary before distributed takeover
- The new job-level contract is deliberately not wired to a worker/takeover path yet. It is a single-node/POSIX durable contract and must be moved to the production job/DB ledger, with external side effects accepting the same idempotency key, before distributed takeover.
- This file-backed contract is sufficient for the current service's deterministic step handlers and single-node/POSIX execution model.
- Do **not** enable distributed late acknowledgements, worker takeover or external side effects on this path yet. Before activation, move the idempotency ledger to the durable job/DB layer and make each external side effect accept the same idempotency key.

### Next acceptance gates
- Duplicate delivery leaves one durable outcome.
- Retry exhaustion produces an inspectable failure state.
- Provider outage fails over without bypassing consent.
- Myanmar/English retrieval benchmark meets the configured threshold.
- AI-generated organization actions remain approval-gated.

## Phase 9 — Controlled Product Expansion

### Objectives
- Organization lifecycle, membership, invitations and RBAC.
- Tenant-scoped documents, sharing and audit trails.
- Strong authorization at API, database/RLS and storage boundaries.

### Non-negotiable contracts
- Every organization-scoped read/write carries an authorization context.
- UPDATE policies use both row visibility and ownership/tenant checks.
- Cross-tenant access returns the same safe denial shape as missing resources.
- Invitations expire and are single-use.
- Role changes and membership removal are audited and invalidate privileged sessions where required.

### Activation evidence
- Two tenants × two users isolation matrix.
- RLS policy/advisor clean run.
- Storage object isolation.
- Invitation replay/expiry test.
- Rollback of membership migration.

## Phase 10 — Scale & Reliability

### Objectives
- Durable queues, leases, idempotency keys, bounded retries and DLQ.
- Capacity/load baselines and failure-mode drills.
- Backup/restore and disaster recovery objectives.

### Contracts
- No infrastructure degradation may silently downgrade correctness.
- Every async job has a stable idempotency key.
- Lease expiry permits safe takeover without duplicate side effects.
- Retries are bounded and observable.
- DLQ entries retain enough metadata to replay safely without secrets.

### Activation evidence
- Duplicate delivery test.
- Worker crash/takeover test.
- Retry/DLQ test.
- Load baseline with documented p95/p99 and error budget.
- Restore drill against a disposable environment.

## Phase 11 — Advanced Intelligence

### Objectives
- Multilingual RAG, embeddings, reranking and semantic search.
- Provider cost/quality routing and feedback-driven evaluation.
- Provenance-preserving answer generation.

### Contracts
- Every retrieved answer can point back to source document/page/chunk.
- Evaluation uses fixed benchmark sets before provider/model changes.
- Low confidence triggers human review rather than silent fabrication.
- Reader → Planner → Human Approval → Executor remains the protected path for consequential actions.

### Activation evidence
- Myanmar/English retrieval benchmark.
- Citation/provenance completeness.
- Hallucination/abstention test.
- Cost/latency/quality comparison across enabled providers.

## Phase 12 — Enterprise / Mobile / Multi-region

### Objectives
- Governance, mobile production workflows, resumable/offline upload.
- Data residency and region-aware storage.
- Multi-region failover and recovery.

### Contracts
- Mobile offline writes are idempotent and conflict-safe.
- Region selection is explicit and auditable.
- Cross-region replication never bypasses tenant isolation.
- Failover and failback are tested independently.

### Activation evidence
- Mobile offline/resume matrix.
- Region residency test.
- Regional outage drill.
- Restore/failback verification.
- Enterprise audit/export verification.

## Phase 13 — Ecosystem / API Platform

- Versioned public APIs, webhooks, SDK contracts and integration sandbox.
- Per-client quotas, signing, replay protection and deprecation policy.
- Acceptance: signed webhook replay/forgery matrix and backward-compatibility suite.

## Phase 14 — Intelligent Operations

- Operational SLOs, anomaly detection, incident correlation and automated runbooks.
- Alert deduplication, retention and escalation policy.
- Acceptance: injected failure → alert → diagnosis → mitigation → recovery evidence.

## Phase 15 — Data Intelligence

- Governed analytics, lineage, retention, exports and privacy-safe aggregation.
- Benchmark data quality and schema evolution.
- Acceptance: lineage completeness, retention/purge verification and export/import round trip.

## Phase 16 — Global Platform

- Regional routing, localization, timezone/currency handling and regional service policies.
- Acceptance: regional configuration matrix and cross-region isolation/recovery drill.

## Phase 17 — Ecosystem Scale

- Marketplace/integration catalog, partner controls, capability discovery and sandboxing.
- Acceptance: tenant-scoped integration credentials, quota enforcement and revocation tests.

## Phase 18 — Continuous Reliability / Governance

- Long-lived compatibility, dependency lifecycle, security posture, chaos drills and release governance.
- Acceptance: quarterly recovery/security drill, dependency closure, rollback rehearsal and signed release evidence.

## Release discipline

For every phase:
1. Build behind a flag or isolated route.
2. Add unit/contract tests.
3. Add negative/security tests.
4. Add migration and rollback before activation.
5. Establish performance/cost baseline.
6. Run disposable acceptance environment.
7. Record privacy-safe evidence.
8. Activate only after the evidence gate passes.


## Contract backlog prepared during Train 0 closure

### Train 1 — Workflow + AI Hardening
1. Durable job-level idempotency key and state machine.
2. Explicit retryable/non-retryable error taxonomy.
3. Retry exhaustion state and DLQ transition.
4. Provider circuit breaker: closed → open → half-open → closed/open tests.
5. Provider failover must preserve request identity, consent and output schema.
6. Consent boundary must be enforced before any external AI provider call.
7. Structured AI output schema validation must fail closed on invalid output.
8. OCR/multilingual retrieval contract must preserve language metadata and avoid cross-language corruption.
9. Human approval boundary must be explicit for destructive/externally visible actions.

### Train 2 — Controlled Product Expansion
- Contract-first organization lifecycle and membership transitions.
- Tenant authorization matrix mapped to RLS and storage ownership.
- Invitation expiry, replay and session invalidation tests.
- Migration forward/rollback pair and acceptance evidence.

### Train 3 — Scale & Reliability
- Queue lease contract with owner, lease expiry and fencing token.
- Duplicate delivery must converge to one durable outcome.
- Retry budget and DLQ transition must be observable and replay-safe.
- Load baseline and failure-injection scenarios before traffic expansion.
- Restore drill must measure RTO and explicitly state the RPO model.

### Train 4–18 preparation
Each later phase retains the same activation sequence: contract → implementation → feature flag → migration → rollback → security review → performance baseline → acceptance evidence → activation. No later-train feature is activated merely because its documentation or tests exist.


## Train 1 safety contract checkpoint
- Implemented contract layer for retry taxonomy/exhaustion, DLQ completeness, circuit breaker state transitions, explicit failover approval, consent scope, fail-closed structured output, mya/eng retrieval constraints, and human approval.
- These contracts remain provider/queue agnostic. They must be wired into concrete integrations before runtime acceptance; distributed worker takeover remains disabled.
