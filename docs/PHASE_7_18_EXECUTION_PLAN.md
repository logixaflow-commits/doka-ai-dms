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
- AI provider fallback/circuit breaker and schema validation exist.
- Organization planning is review-only by default.
- Workflow engine now rejects empty/invalid step definitions and rejects stale/wrong-step completion.

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
