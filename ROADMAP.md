# Doka Roadmap

## Final goal
Release Doka only when required real evidence passes. Code existence or green CI alone is not release evidence.

Personal Local: login -> copied-source import -> scan/OCR -> review -> human approval -> Final copy -> backup -> isolated restore -> undo, with unchanged source hashes.

Cloud: authenticated lifecycle -> two-user isolation -> storage/recovery -> security settings -> deployment/runtime evidence.

## Completed phases
- Phase A–E: historical remediation tracks; evidence retained in archive.
- Phase 0: completeness/documentation inventory.
- Documentation migration Phases 1–6.
- Core coding-side foundations: architecture, security, workflow reliability, AI/provider boundaries, and CI/quality foundations substantially implemented.
- Quality gate: dependency/secret/lockfile/lint/CodeQL evidence recorded.
- Cloudflare Worker current deployment evidence verified on 2026-10-08.
- Render service absence verified for the connected workspace.
- Cloudinary provider-level recovery probe verified on 2026-10-08.

## Active release phase — Personal Local
1. Gate 1 — Local auth/session/restart/replay.
2. Gate 2 — Organization Apply/locking/limits/Undo.
3. Gate 3 — OCR resource limits + Myanmar/English benchmark.
4. Gate 4 — Real browser Personal Local E2E.
5. Gate 5 — Copied-office pilot + source before/after hashes.
6. Gate 6 — Backup/restore + measurable RTO/RPO.
7. Gate 7 — Dependabot/secret-scan/lockfile/lint reconciliation.
8. Gate 8 — Personal Local final freeze and release evidence.

Gates 1, 2 and 7 have automated/code-side evidence. Gates 3–6 still require real evidence. Gate 8 remains blocked until 1–7 are evidenced. The current execution order is Gate 3 OCR → Gate 5 copied-office pilot/recovery → Gate 4 browser E2E → Gate 6 timed recovery/RTO/RPO → Gate 7 dependency/security recheck → Gate 8 final freeze.

### Current close-out evidence
- Gate 3: PENDING. OCR runner exists, but current representative sample/manifest and Tesseract version are unavailable.
- Gate 4: PENDING. The current Playwright suite is prepared and validated for discovery/build integration, but a real browser run with a copied acceptance dataset and local admin password is still required.
- Gate 5: PENDING. The pilot/hash harness now also verifies backup integrity and isolated recovery; only representative copied-office evidence remains.
- Gate 6: PENDING. The pilot now captures backup creation, verification and isolated-restore timings plus zero-loss-at-backup-point evidence; a real-machine timed recovery drill is still required to establish release RTO/RPO targets.
- Vercel: VERIFY for explicit owner-paused state because the connected API exposes live=false/latest production CANCELED but no explicit paused flag.

## Cloud release phase
9. Gate 9 — Authenticated Cloud lifecycle E2E.
10. Gate 10 — Two-user isolation + RLS/Storage/RPC proof.
11. Gate 11 — B2/Cloudinary/Google Drive + 50 MiB + recovery proof.
12. Gate 12 — Deployment/runtime evidence and final go-live sign-off.

### Current close-out evidence
- Gate 9: PENDING. An authenticated cloud acceptance runner is now prepared for user-A lifecycle plus exact 50 MiB boundary; real tokens/runtime evidence are still required.
- Gate 10: PENDING. The same runner now includes two-user document isolation checks; live Supabase/RLS/Storage proof still requires two distinct authenticated users.
- Gate 11: PENDING. Provider routing/unit coverage exists for Supabase/B2/Cloudinary/Google Drive, but real B2 + Google Drive recovery and Cloudinary application-path evidence remain required.
- Gate 12: BLOCKED by Gates 9–11.

## Future phases
### Phase 7/8 — Workflow + AI hardening
Stronger workflow reliability, durable job-level idempotency, retry/DLQ contracts, provider quality/cost routing, multilingual retrieval and advanced AI safety after core release.
Durable job idempotency contract is implemented/tested on `main`; distributed queue takeover remains deferred until production job/DB persistence and external-side-effect idempotency are complete.

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

## Verification and future backlog — preserved from Phase 0 ledger
### Release/live verification backlog
- Real Cloudinary application-path E2E.
- Real Supabase Storage E2E.
- Real B2 E2E.
- Real Google Drive E2E.
- Signed QStash delivery verification.
- QStash -> workflow completion verification.
- Workflow retry/recovery verification.
- Duplicate-delivery protection verification.
- Production authentication/API smoke tests.
- Production monitoring/failure-mode checks.
- End-to-end RAG ingest -> embed -> search.
- Agent -> Brain -> publish E2E.
- Workflow approval -> resume -> completion.
- Scheduled workflow across a real time boundary.
- Newsletter delivery E2E.
- External-provider failover test.

### Future quality/product backlog
- Universal source -> publish E2E.
- Preserve source provenance to file/page/sheet/row/URL.
- SEO/news quality validation.
- Real production storage/provider validation before any universal publishing claim.
- Paginated chat restore.
- Transcript export.
- Explicit retention controls.
- Administrator lookup.
- Transfer confirmation.
- Role-based transfer permissions.
- Reviewable retention policy.
- Approved purge workflow.
- Session activity search.
- Operational audit reporting for sessions.
- Persist RAG metrics and alert history.
- Real notification adapter.
- Rate/window alert policies.
- Durable alert retention/pagination/export.
- Read-only/configuration role separation for RAG dashboard.
- Durable quality feedback.
- Experiment assignment and statistical analysis.
- Cancellable async search.
- Database index telemetry.
- Isolated backend test database/fixtures.
- Supported notification provider/threat-model decision.
- Durable metrics retention and deduplication.
- Correlation-ID investigation runbook.
- Threshold-tuning runbook.
- Future complex AI workflows.
- More external integrations.
- Stronger durable job execution.
- Expanded RAG capabilities.
- Advanced analytics/business intelligence.
- Broader observability and operational controls.
- Broader supply-chain intelligence coverage.

### Deferred AI/provider verification
- Final AI-agent live verification.
- Real provider credentials plus authenticated production tests.
