# Doka Roadmap

## Final goal
Release Doka only when required real evidence passes. Code existence or green CI alone is not release evidence.

Personal Local: login -> copied-source import -> scan/OCR -> review -> human approval -> Final copy -> backup -> isolated restore -> undo, with unchanged source hashes.

Cloud: authenticated lifecycle -> two-user isolation -> storage/recovery -> security settings -> deployment/runtime evidence.

## Completed phases
- Phase A–E: historical remediation tracks; evidence retained in archive.
- Phase 0: completeness/documentation inventory.
- Core Phase 1–6 coding-side foundations: architecture, security, workflow reliability, AI/provider boundaries, and CI/quality foundations substantially implemented.
- Quality gate: dependency/secret/lockfile/lint/CodeQL evidence recorded.

## Active release phase — Personal Local
1. Gate 1 — Local auth/session/restart/replay.
2. Gate 2 — Organization Apply/locking/limits/Undo.
3. Gate 3 — OCR resource limits + Myanmar/English benchmark.
4. Gate 4 — Real browser Personal Local E2E.
5. Gate 5 — Copied-office pilot + source before/after hashes.
6. Gate 6 — Backup/restore + measurable RTO/RPO.
7. Gate 7 — Dependabot/secret-scan/lockfile/lint reconciliation.
8. Gate 8 — Personal Local final freeze and release evidence.

Gates 1, 2 and 7 have automated/code-side evidence. Gates 3–6 still require real evidence. Gate 8 remains blocked until 1–7 are evidenced.

## Cloud release phase
9. Authenticated Cloud lifecycle E2E.
10. Two-user isolation + RLS/Storage/RPC proof.
11. B2/Cloudinary/Google Drive + 50 MiB + recovery proof.
12. Deployment/runtime evidence and final go-live sign-off.

## Future phases
### Phase 7/8 — Workflow + AI hardening
Stronger workflow reliability, provider quality/cost routing, multilingual retrieval and advanced AI safety after core release.

### Phase 9 — Controlled Product Expansion
Enterprise organizations, membership lifecycle, invitations, RBAC, org-scoped sharing and regulated-workload controls. Activation requires tenant isolation, RLS/API authorization, audit and rollback evidence.

### Phase 10 — Scale & Reliability
Distributed leases, queues, idempotency, bounded retries, DLQ, load/capacity and disaster recovery. Missing infrastructure must never silently downgrade correctness.

### Phase 11 — Advanced Intelligence
Multilingual RAG, embeddings/reranking benchmarks, provider cost/quality routing, feedback and semantic search. Reader -> Planner -> Human Approval -> Executor remains mandatory.

### Phase 12 — Enterprise/Mobile/Multi-region
Team governance, production mobile, resumable/offline upload, data residency and multi-region recovery, each with independent acceptance evidence.

### Phase 13–18 — Ecosystem / Operations / Data / Global
Ecosystem and API platform, intelligent operations, data intelligence, regional/global platform capabilities. Each is an independent feature train requiring feature flag/activation, migration/rollback, security review, performance baseline and acceptance evidence.

## Deferred
- Enterprise production activation.
- Cloud-first architecture variants from archived documents.
- Unverified external providers and integrations.
- Any provider claim based only on configured credentials.

## Blocked
- Gate 8 by Gates 1–7.
- Gate 12 by Gates 9–11.

## Backlog
- Chat restore pagination, transcript export, retention controls, administrator lookup, transfer permissions, session activity/audit search.
- Durable RAG metrics/alert history, notification adapters, alert policies, retention/export, quality feedback and experiment analysis.
- Cancellable async search, database index telemetry, isolated backend test database/fixtures.
- Universal source-to-publish workflows, provenance to file/page/sheet/row/URL, SEO/news quality validation.
- Additional external integrations, stronger durable jobs, broader RAG, advanced analytics and observability.

## Release rule
Every phase closes only after implementation, automated tests, required E2E/live verification, acceptance criteria, evidence recording, and documentation updates. Status vocabulary: DONE / VERIFIED / PENDING / BLOCKED / DEFERRED / NEXT / VERIFY.
