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
- Cloudflare Worker current deployment evidence verified on 2026-10-09 (version 652 at 100% traffic).
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

Gates 1, 2 and 7 have automated/code-side evidence. Gates 3–6 still require real evidence. Gate 8 remains blocked until 1–7 are evidenced. The current execution order is Gate 3 OCR → Gate 5 copied-office pilot/recovery → Gate 4 browser E2E → Gate 6 timed recovery/RTO/RPO → Gate 7 dependency/security recheck → Gate 8 final freeze. Latest local checks on 2026-10-09: maintained Personal Local backend suite 58 passed; Cloud storage/provider/release-gate/D1 migration suite 90 passed; frontend install/build/smoke/lint/audit passed on Node 24.21.0. Local pip-audit reports for six backend profiles plus the root project had zero unignored findings. GitHub Actions run 38072383164 passed all nine reported jobs on commit c470c260d38de59766b90b3f1d8c0ecd55d625c3; the later current HEAD (8094733592ec9255a093d52610bdc0c9ee733d07) still needs its own directly associated run.
- D1 authorization migration 0002 was applied after export-and-restore preflight. The post-change production D1 query found the unique-owner index and all six integrity triggers expected by the migration; the affected metadata tables remain empty. Privacy-safe evidence is recorded under `Phase0_Evidence/train1/d1-authorization-migration-2026-10-09.json`.
  Boundary: the deployed document metadata path remains Supabase-backed, so Gate 10 still requires live Supabase RLS/API isolation evidence; D1 migration success does not close it.

### Current close-out evidence
- Gate 3: PENDING/BLOCKED. The benchmark now enforces mean CER ≤0.30 and mean WER ≤0.60 by language label. The latest six-sample report correctly fails: the single Myanmar/English sample has CER 79.94% and WER 171.43%. The reference text still needs visual verification against the rendered scan, followed by a representative rerun; code/CI alone cannot close this gate.
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
- Gate 9: PENDING. An authenticated cloud acceptance runner is now prepared for user-A lifecycle plus exact 50 MiB boundary; real tokens/runtime evidence are still required; runner cleanup and failure evidence paths are now hardened.
- Gate 10: PENDING. The runner now follows the current signed direct-upload/completion/download contract and verifies actual bytes; it includes two-user document isolation checks. Live Supabase/RLS/Storage proof still requires two distinct authenticated users and a dedicated acceptance environment.
- Gate 11: PENDING. Provider routing/unit coverage exists for Supabase/B2/Cloudinary/Google Drive, but real B2 + Google Drive recovery and Cloudinary application-path evidence remain required.
- Gate 12: BLOCKED by Gates 9–11.

## Future phases
### Phase 7/8 — Workflow + AI hardening
Stronger workflow reliability, durable job-level idempotency, retry/DLQ contracts, provider quality/cost routing, multilingual retrieval and advanced AI safety after core release.
Durable job idempotency contract is implemented on `main`, with focused contract tests added and a disposable smoke validation passing; distributed queue takeover remains deferred until production job/DB persistence and external-side-effect idempotency are complete.

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

- Train 1 contract layer now covers retry/DLQ, circuit breaker, failover, consent, schema, multilingual retrieval and human approval; concrete integration and runtime evidence remain before Train 2 activation.


## Train 1 integration checkpoint — 2026-10-08

Train 1 is beyond contract-only work. Concrete repository paths now enforce:

- durable D1 job idempotency over the existing jobs table schema;
- retryable vs non-retryable outbox delivery with bounded retry/dead transitions;
- AI provider circuit breaking, conservative retry classification, explicit failover approval, consent and fail-closed provider output handling;
- OCR-aware Myanmar/English retrieval with Unicode NFC normalization, identity/hash validation and language-scoped ranking.

The next Train 1 exit step is evidence, not speculative wiring: D1 runtime requires a provisioned database, provider acceptance requires real configured providers/consent, and multilingual retrieval requires the representative benchmark. Train 3 lease/fencing/takeover remains gated until those prerequisites and external-side-effect idempotency are proven.

## Consolidated remaining-work register — 2026-10-11

This register consolidates release gates, Train 1/3 work, deferred future phases, and the preserved Phase 0 backlog. A row is not complete merely because a runner, adapter, contract, or test exists.

### P0 — required before Personal Local release

- [ ] Gate 3 — OCR quality: visually compare the Myanmar reference with the rendered scan; correct the reference if wrong; collect representative English and Myanmar samples; rerun with Tesseract eng/mya; meet per-language mean CER <= 0.30 and mean WER <= 0.60; resolve the three copied-office OCR timeouts and rerun the complete pilot. Keep the gate blocked if quality or execution fails.
- [ ] Gate 4 — representative browser E2E: run authenticated login -> copied-office import -> scan/OCR -> understand -> review/approval flow against representative copied data; preserve before/after source hashes; capture privacy-safe evidence and fix all timeout or workflow failures.
- [ ] Gate 5 — copied-office pilot: execute the complete pilot on the authorized office copy, verify all source hashes remain unchanged, validate workspace/backup separation, and retain redacted evidence.
- [ ] Gate 6 — recovery objectives: run a real-machine backup, integrity verification, isolated restore, and comparison drill; measure backup and restore durations; declare achievable RTO/RPO targets and prove them.
- [ ] Gate 7 — freeze recheck: rerun dependency, secret, lockfile, lint, CodeQL/SBOM and security checks on the exact release commit; resolve or explicitly disposition every finding.
- [ ] Gate 8 — release freeze: close Gates 1–7 with evidence, document known limitations, and sign off only after a clean final regression run.

### P0 — required before Personal Cloud go-live

- [ ] Gate 9 — authenticated lifecycle: run cloud acceptance with dedicated real test-user credentials; prove upload/session/completion/download/delete lifecycle and exact 50 MiB boundary behavior; verify downloaded bytes and cleanup.
- [ ] Gate 10 — tenant isolation: use two distinct authenticated users to prove cross-user document/API/storage denial; verify live Supabase RLS, Storage policies, RPC privileges, and application authorization. Synthetic tests alone are insufficient.
- [ ] Gate 11 — providers and recovery: verify B2 and Google Drive live upload/export/restore paths, Cloudinary application-path behavior, >50 MiB routing, byte integrity, failure cleanup, and provider recovery. Provider-unit tests or credentials being configured do not count.
- [ ] Security settings: enable Supabase Auth leaked-password protection through an authorized project operator and rerun the Security Advisor; retain the current warning as a blocker until verified.
- [ ] Runtime/deployment: confirm the intended runtime and secret store, verify provider key reachability without exposing secret values, and run authenticated production-like smoke/failure-mode tests. Keep Vercel production paused until owner approval; do not infer that a canceled deployment is a successful release.
- [ ] Gate 12 — final sign-off: require Gates 9–11, deployment/runtime evidence, rollback readiness, monitoring, and explicit passed: true sign-off.

### P1 — Train 1/3 reliability and AI activation

- [ ] Wire consent to a trusted, persisted grant lifecycle: authenticated subject identity must come from server-side auth; purpose and exact document/resource scope must be server-derived; revocation and audit must be supported; clients must not be able to mint trusted grants. Until that exists, external AI calls without a trusted grant must remain fail-closed.
- [ ] Verify the free-only AI policy end-to-end with an approved free model and embedding model, real runtime configuration, explicit consent, schema-invalid responses, provider failure, circuit recovery, and failover disabled/enabled cases; confirm no billable provider adapter is reachable.
- [ ] Re-run focused AI/idempotency/OCR tests and the maintained suite on the exact HEAD; associate direct GitHub Actions results with that SHA. Run tests in a provisioned test environment because this workspace has no pytest module installed.
- [ ] Verify representative OCR-aware Myanmar/English retrieval quality, source identity/hash validation, Unicode normalization, and deterministic ranking.
- [ ] Verify retry taxonomy, bounded retry exhaustion, DLQ visibility/replay policy, duplicate delivery, signed QStash delivery, QStash -> workflow completion, approval -> resume -> completion, and a scheduled workflow crossing a real time boundary.
- [ ] Keep distributed worker takeover, lease/fencing and queue consumers disabled until persistent ownership, crash recovery, and external-side-effect idempotency are proven.

### P2 — cloud and integration backlog

- [ ] Real Supabase Storage E2E and two-user RLS/API proof.
- [ ] Real B2 E2E, Google Drive export/recovery, and full Cloudinary application-path E2E.
- [ ] Production authentication/API smoke tests, monitoring, and failure-mode drills.
- [ ] End-to-end RAG ingest -> embed -> search; persisted RAG metrics/alert history; notification adapter and rate/window policies; durable alert retention/pagination/export; dashboard role separation; quality feedback and statistically meaningful experiment analysis.
- [ ] Agent -> Brain -> publish E2E; approval -> resume -> completion; universal source -> publish E2E; source provenance down to file/page/sheet/row/URL; SEO/news quality validation.
- [ ] Chat restore pagination, transcript export, explicit retention and approved purge controls, administrator lookup, transfer confirmation and role permissions, session activity/audit search and operational audit reporting.
- [ ] Cancellable async search, database index telemetry, isolated backend test database/fixtures, correlation-ID investigation and threshold-tuning runbooks, supply-chain intelligence coverage, and broader operational observability.

### P3 — future product trains (activation gated)

- [ ] Phase 9 — Controlled Product Expansion: enterprise organizations, membership lifecycle, invitations, RBAC, organization-scoped sharing, regulated-workload controls. Exit: tenant isolation, RLS/API authorization, audit trail, migration/rollback, and acceptance evidence.
- [ ] Phase 10 — Scale & Reliability: distributed leases/queues/idempotency, bounded retries, DLQ, load/capacity tests, disaster recovery. Exit: crash/replay/duplicate tests and measured capacity/recovery; no silent downgrade of correctness.
- [ ] Phase 11 — Advanced Intelligence: multilingual RAG, embedding/reranking benchmarks, provider cost/quality routing, feedback, semantic search. Exit: benchmarked quality/cost, persisted telemetry, exact-scope consent, schema fail-closed, human approval, and live provider evidence.
- [ ] Phase 12 — Enterprise/Mobile/Multi-region: team governance, production mobile, resumable/offline upload, data residency, multi-region recovery. Each capability requires its own threat model, migrations/rollback, performance baseline, and acceptance.
- [ ] Phases 13–18 — Ecosystem / Operations / Data / Global: API/ecosystem platform, intelligent operations, data intelligence, regional/global capabilities. Scope each train before implementation and require feature flags, migration/rollback, security review, capacity baseline, observability, and acceptance evidence.
- [ ] Enterprise activation: remains deferred until all tenant/security/operational prerequisites pass. Archived cloud-first variants remain historical, not an active architecture commitment.

### Owner/environment-dependent evidence (not safely fabricatable from repository CI)

The following need a real authorized environment or operator action: visual OCR reference validation and representative office scans; office-copy full pilot; real-machine measured recovery; dedicated authenticated cloud test users/tokens; B2 and Google Drive access; approved provider credentials/consent; Supabase Auth security-setting change; and owner approval to reactivate Vercel production. Everything else that can be implemented or tested in-repository should be completed before asking for these inputs.

### Exact-HEAD CI rule

Run 38072383164 passed its nine reported jobs on commit c470c260d38de59766b90b3f1d8c0ecd55d625c3; it is not evidence for later commits. The current main history must have a directly associated successful CI run before this register can mark the latest code as CI-verified.
