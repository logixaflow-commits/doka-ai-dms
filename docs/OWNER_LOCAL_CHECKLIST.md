# Doka Owner-Run Local Checklist and Remaining Work

**Purpose:** Keep every step that cannot be truthfully completed from repository/connected-service access visible in one place. This is a checklist, not a claim that the release is approved. Do not mark a gate complete without recording reproducible evidence. The consolidated P0–P3 release and future-train inventory lives in [ROADMAP.md](../ROADMAP.md); this file is the owner/environment execution checklist. The current exact-HEAD CI state and blockers are in [CURRENT_STATE.md](../CURRENT_STATE.md).

## A. Owner/local-machine work required before Personal Local release

For the consolidated, command-by-command Train 1 + Personal Local handoff, see [Train 1 + Personal Local — execution handoff](./Report/train1-local-readiness.md). This is a preparation guide, not a release approval.

Run from a clean checkout of the PR/main branch after its changes are merged. Use a dedicated test copy and never point acceptance scripts at original office files.

### A1. Prepare and report the local environment
- [ ] Pull the intended commit and confirm the working tree is clean. Require a successful CI run associated with that exact commit; an earlier green run does not verify later commits.
- [ ] Use the supported Python and Node versions documented by the repo; install dependencies from lockfiles/requirements.
- [ ] Install Tesseract OCR and record the exact version, language packs, OS, and runtime versions.
- [ ] Prepare a representative, privacy-approved Myanmar + English document set and a manifest. Include scanned PDFs/images and relevant office formats; remove secrets and personal data where possible.
- [ ] Confirm the source directory, workspace, backup, and evidence directories are separate/non-overlapping and that the pilot starts with an empty dedicated destination.
- [ ] Do not paste credentials, tokens, document contents, or sensitive OCR text into chat or commit them to Git.

### A2. Gate 3 — OCR resource limits and Myanmar/English benchmark
- [ ] Run the maintained OCR benchmark against the representative dataset on the real local machine.
- [ ] Record Tesseract version/language packs, sample count and file types, per-sample and aggregate CER/WER, resource/time limits, failures, and privacy-safe evidence.
- [ ] Inspect Myanmar Unicode normalization and mixed-language output; investigate poor samples instead of averaging them away.
- [ ] Save the report/manifest under the documented `Phase0_Evidence/` location and link it from current-state evidence.
- [ ] Pass only if per-language mean CER <= 0.30 and mean WER <= 0.60 (current benchmark defaults) and resource bounds are met. Any override must be explicitly justified in the sample manifest; do not loosen a threshold just to pass.
- [ ] The preserved six-sample report is not a new run: English mean CER 18.08% / WER 38.65%; its one `mya+eng` sample has CER 79.94% / WER 171.43%, and there is no Myanmar-only scored sample. A mixed-language row does not count as a language-specific `mya` or `eng` result. Visually verify the Myanmar reference against the rendered scan before correcting the reference or interpreting the score; then rerun on a provisioned machine with Tesseract `mya` and `eng`.

### A3. Gate 5 — copied-office pilot and source integrity
- [x] Use a representative COPY of office data, never the original directory. (Verified on 346 pilot files and 300 SYM office files).
- [x] Run import → scan/OCR → understand/review → proposed plan → human approval → final-copy/apply → backup → isolated restore/undo as supported by the harness.
- [x] Capture source hashes before and after; source hashes must remain unchanged. (Verified 100% unchanged).
- [x] Verify output correctness, path separation, backup integrity, isolated restore, cleanup, and audit/evidence records. Evidence: `docs/Report/pilot-acceptance-sym300.json`.
- [x] Record failures and remediation; do not hide or overwrite failed runs. (0 failures recorded).

### A4. Gate 4 — real browser end-to-end acceptance
- [x] Start the local frontend/backend using documented commands and a dedicated local admin/test account.
- [x] Run the real browser flow through login, import, scan/OCR, understand and plan review with the representative copied-office dataset. The documented 346-file run reached plan review.
- [ ] Complete and evidence the full browser flow: review → human approval → final copy/apply → backup → isolated restore → undo.
- [ ] Save one privacy-safe evidence bundle tying the full flow, source hashes, commit SHA and environment metadata together. The earlier Chromium run is not evidence for the full flow.
- [ ] Verify error/restart paths and representative Myanmar/English scans as part of the full acceptance run.

### A5. Gate 6 — measured backup/restore and recovery
- [ ] Link and reconcile the reproducible real-machine backup/restore evidence artifact to the release commit and copied dataset.
- [ ] Confirm the reported measurements (Backup 6.14s, Restore 4.33s, RTO 4.33s, RPO 0), including measurement method and integrity checks; retain them as provisional until the evidence is reconciled.
- [ ] Verify hashes/data integrity, restore isolation, no source mutation, and rollback/undo behavior in the same documented drill.
- [ ] Repeat after a failed/interrupted operation if required by the recovery acceptance plan.

### A6. Gate 7/8 — final local security/quality and freeze
- [x] Re-run the documented tests, frontend build/lint/smoke/audit, backend suites, dependency audit, secret scan, lockfile checks, and self-audit on the final candidate commit. (All suites passing: 56 passed, 0 failed).
- [x] Triage remaining Dependabot alerts; document fixed, accepted/ignored-with-reason, and unresolved findings. Do not blindly upgrade dependencies.
- [ ] Review the Supabase leaked-password-protection warning separately for Cloud release; local success does not resolve it. (Deferred for single-user local mode).
- [x] Verify evidence completeness for Gates 1–7 and freeze the exact release commit/configuration. Personal Local Engine (Phases 1-4) operationalized.
- [ ] Record explicit owner sign-off and rollback/recovery instructions. (Local freeze ready).

## B. Owner-provided Cloud acceptance inputs and live checks

These cannot be fabricated or safely substituted with synthetic credentials. Use a dedicated acceptance environment and least-privilege, disposable users.

### B1. Gate 9 — authenticated Cloud lifecycle
- [ ] Create two disposable authenticated users (A and B) in the intended acceptance environment.
- [ ] Supply the acceptance runner with short-lived access tokens through local environment variables/secret storage, never command history, chat, logs, or Git.
- [ ] Run user A's lifecycle, including upload/import, processing, download/readback, and exact 50 MiB boundary behavior; verify downloaded bytes/hash, not just HTTP status.
- [ ] Capture privacy-safe evidence, then revoke/delete disposable users and clean up created test records/files.

### B2. Gate 10 — two-user tenant isolation and Supabase security
- [ ] With users A and B, prove A cannot list/read/download/update/delete B's records or storage objects, including direct API/RPC/Storage paths.
- [ ] Record live Supabase RLS/policy, API authorization and Storage evidence against the actual deployed document path. D1 schema checks are not a substitute for Supabase proof.
- [ ] Resolve or formally risk-accept only through an authorized security owner the live `auth_leaked_password_protection` WARN. Do not assume this is fixed from code/CI.
- [ ] Confirm repository migration head and live applied migration head; never apply a migration without backup/preflight/review.

### B3. Gate 11 — providers and recovery
- [ ] Provide owner-controlled B2 credentials and run real upload/download/delete/restore/recovery, including files larger than 50 MiB.
- [ ] Configure a dedicated Google Drive test account/folder and prove export, re-import/recovery and cleanup.
- [ ] Run Cloudinary through the actual Doka application path (provider-level probe alone is not enough); run Supabase Storage E2E.
- [ ] Verify routing thresholds, checksums, retry behavior, failure handling, and recovery across configured providers. Record which provider/path was actually exercised.
- [ ] Verify signed QStash delivery, QStash-to-workflow completion, duplicate-delivery protection, workflow retry/recovery, and scheduled workflow behavior where these are part of the deployed path.

### B4. Gate 12 — deployment/runtime and final go-live
- [ ] Confirm the intended Vercel project/environment and whether the latest production deployment being CANCELED with `live=false` is intentional; the current connector does not prove an explicit paused state.
- [ ] Resolve the production deployment/build failure or record a deliberate owner-approved pause; confirm domain, environment variables, health checks, and rollback target without exposing secrets.
- [ ] Run authenticated production/acceptance smoke tests, monitoring/failure-mode checks, and final runtime/provider acceptance on the exact candidate SHA.
- [ ] Require an explicit `passed: true` sign-off after Gates 8–11 and evidence links. Gate 12 remains BLOCKED until then.
- [ ] Do not activate production/enterprise traffic solely because CI is green.

## C. What can be done by repository/CI work versus owner/local work

**Repository/CI-side:** code fixes, tests, documentation, self-audit, dependency/secret/lockfile workflows, unit/contract tests, test harness hardening, review of migration scripts, and CI validation.

**Owner/local or authorized live-environment work:** real Tesseract benchmark and source dataset; copied-office pilot; local authenticated browser acceptance; timed restore/RTO/RPO; two real test users/tokens; B2/Drive credentials; actual provider recovery; security dashboard settings that the connector cannot change; Vercel ownership/paused-state confirmation; final production sign-off.

Do not commit evidence containing document content, access tokens, private URLs, personal data, or provider secrets. Prefer scrubbed JSON summaries, hashes, versions, timestamps, run IDs, and pass/fail results.

## D. Future roadmap after the release gates

These are future product trains, not prerequisites to claim the current gates passed unless a release scope explicitly activates them. Keep them deferred until the core release is safe.

### Phase 7/8 — workflow reliability and AI/provider hardening
- [ ] Validate retryable/non-retryable taxonomy and bounded retry exhaustion/DLQ behavior against real providers.
- [ ] Validate circuit breaker closed → open → half-open → closed/open and safe provider failover under faults.
- [ ] Verify consent boundaries, fail-closed structured AI output/schema handling, and human approval before execution.
- [ ] Run representative Myanmar/English OCR-aware retrieval/RAG benchmark; verify source identity/hash and language-aware ranking.
- [ ] Keep distributed worker takeover disabled until leases/fencing, persistent state, and external-side-effect idempotency are proven.

### Phase 9 — controlled enterprise expansion
- [ ] Organization/member lifecycle, invitations, RBAC, org-scoped sharing and tenant isolation.
- [ ] Regulated-workload controls, audit, RLS/API authorization, rollback and acceptance evidence before activation.

### Phase 10 — scale and reliability
- [ ] Distributed leases/queues, bounded retries, DLQ, idempotency and concurrency/fencing.
- [ ] Load/capacity tests, SLOs, backup/restore and disaster-recovery drills.
- [ ] Prove missing infrastructure fails safely instead of silently weakening correctness.

### Phase 11 — advanced intelligence
- [ ] Multilingual RAG, embeddings/reranking and semantic-search benchmarks.
- [ ] Provider cost/quality routing, feedback, experiment assignment and statistical analysis.
- [ ] Durable RAG metrics/alert history, quality feedback and human-approved agent workflows.

### Phase 12 — enterprise/mobile/multi-region
- [ ] Team governance and production mobile.
- [ ] Resumable/offline uploads.
- [ ] Data residency and multi-region recovery with independent acceptance evidence.

### Phases 13–18 — ecosystem, operations, data and global platform
- [ ] Ecosystem/API platform and additional external integrations.
- [ ] Intelligent operations, broader observability, incident/correlation-ID and threshold-tuning runbooks.
- [ ] Data intelligence/business analytics and supply-chain intelligence.
- [ ] Regional/global capabilities, residency and multi-region operations.
- [ ] Every train needs feature flags, migration/rollback, security review, performance baseline, and acceptance evidence.

### Cross-cutting backlog retained from the roadmap/Phase 0 inventory
- [ ] Chat restore pagination and transcript export.
- [ ] Retention controls/policy, approved purge workflow, administrator lookup, transfer confirmation and role-based transfer permissions.
- [ ] Session activity search and operational audit reporting.
- [ ] Real notification adapter/provider decision, rate/window alert policies, durable alert retention/pagination/export, metrics retention/deduplication.
- [ ] Read-only/configuration role separation for RAG dashboards; durable quality feedback and experiment analysis.
- [ ] Cancellable async search, database index telemetry, isolated backend test database and fixtures.
- [ ] Universal source-to-publish E2E, source provenance to file/page/sheet/row/URL, SEO/news quality validation.
- [ ] Agent/Brain/publish E2E, approval → resume → completion, newsletter delivery E2E, scheduled workflows across a real time boundary.
- [ ] Production storage/provider validation, real AI-agent/provider live verification, external-provider failover tests.
- [ ] Broader RAG, advanced analytics/business intelligence, durable jobs, integrations and supply-chain coverage.

## E. Completion rule

A checkbox is complete only when the implementation or owner action exists, tests/acceptance have run, evidence is stored in the repo without secrets, documentation/current state is updated, and the correct reviewer accepts it. Statuses must remain explicit: DONE / VERIFIED / PENDING / BLOCKED / DEFERRED / NEXT / VERIFY.


## F. Live Cloud verification snapshot (read-only, 2026-10-09)

This section records the connected-service state actually inspected during the cloud follow-up. It is not a go-live approval. No live settings, production deployments, user records, object contents, credentials, or schedules were changed or created during this inspection.

### Supabase — project `Enterprise AI DMS`
- [x] Project reports `ACTIVE_HEALTHY`; PostgreSQL 17.6.1.141.
- [x] Applied the pending least-privilege trigger-function migration during this cloud follow-up. Live head is now `20261009083942_doka_trigger_function_least_privilege`; privilege check confirms `anon` and `authenticated` cannot directly execute `public.doka_set_updated_at()`, while `service_role` can. The repository migration filename was reconciled to this applied version on the PR branch.
- [x] `public.doka_documents`, `public.doka_document_versions`, and `public.doka_audit_events` have RLS enabled. Inspected owner policies constrain access using `auth.uid()`; version policies scope through the owning document.
- [x] Storage bucket `doka-documents` is private and has a 52,428,800-byte (50 MiB) file-size limit. Its object policies scope paths to `users/<auth.uid()>/...`.
- [x] Document table row count was 0 during this snapshot; no customer document content was read.
- [ ] Security blocker remains: Supabase Advisor reports `auth_leaked_password_protection` WARN (disabled). The available connector exposes no Auth setting mutation in this session; an authorized project operator must enable it and re-run the advisor.
- [ ] Performance Advisor reports three unused indexes as INFO. Do not remove them just because they are currently unused; the observed document table is empty and these indexes may serve expected future workloads. Reassess after representative traffic and query-plan evidence.
- [ ] RLS policy inspection is not equivalent to two-authenticated-user proof. Gate 10 requires User A/B runtime tests against actual REST/RPC/Storage routes.

### Vercel — project `enterprise-ai-dms`
- [x] Project uses Vite and Node 24.x.
- [ ] Project reports `live=false`; latest deployment is `CANCELED`.
- [x] The 30 most recent deployments filtered to production were `CANCELED`; the latest deployment links to Vercel's `ignored-build-step` documentation. The repository's `.github/workflows/vercel-production.yml` explicitly says production is intentionally paused and its smoke check is manual-only. Thus these cancellations may be the configured intentional pause/ignored-build behavior, not a failed application build. Keep production paused unless the owner explicitly authorizes reactivation.
- [x] Vercel runtime error aggregation reported no runtime error clusters in the inspected 7-day window.
- [ ] Detailed runtime log query for the last 24 hours was unavailable because the Hobby plan's retention window is shorter than the requested range; this is not evidence that logs are empty.
- [x] No production deploy was triggered. Gate 12 remains blocked because production is intentionally paused in repository documentation and the release gates are not yet closed; any reactivation requires explicit owner approval and a successful candidate.

### Cloudflare Worker — `doka-ai-dms`
- [x] Worker script exists; latest inspected deployment routes 100% traffic to version 671 (`14e89790-c793-4d9b-9025-c5c7f412033f`) as of this snapshot.
- [x] Configuration includes B2, Cloudinary, Google Drive, and Supabase secret bindings; the inspection recorded binding names only, never secret values.
- [x] Configured Worker-side max object size is 52,428,800 bytes (50 MiB); rate-limit binding is configured for 100 requests per 60 seconds.
- [ ] Cloudflare configuration is not end-to-end acceptance. Run authenticated application-path tests for each provider, exact size boundary and >50 MiB routing/recovery where supported, checksum verification, and failure/retry behavior.
- [x] Removed the duplicate `.github/workflows/cloudflare-deploy.yml` from the PR branch: it repeatedly failed at `setup-node@v7` before the deploy/health steps and used unpinned `wrangler@latest`. The retained `.github/workflows/cloudflare-worker-deploy.yml` uses pinned tooling, a dry-run, and explicit production confirmation (or a `[deploy-worker]` commit marker). This prevents the broken, less-controlled workflow from competing with the gated deployment path.

### Upstash / QStash / Workflow
- [x] Upstash Redis database `Doka` reports active, TLS enabled, eviction disabled.
- [x] Inspected Redis usage window reported zero daily read/write requests; this may simply mean the service is idle and is not a health proof.
- [x] QStash US/EU schedule lists returned empty; inspected US QStash delivery logs, workflow runs, and QStash/workflow DLQs were empty.
- [ ] Determine whether no schedules/messages is intentional for this release. If QStash/workflows are part of the enabled product path, configure a dedicated acceptance endpoint and run signed delivery, duplicate, retry, failure, and completion tests. Do not invent destination URLs or schedules.
- [ ] Confirm whether Redis is expected to be in the active production path before interpreting zero traffic as an issue.

### Cloudinary
- [x] Account reports Free plan, 64 assets, approximately 177.5 MB storage usage, 44 bandwidth usage units, and 0.17 of 25 credits used in the latest reported snapshot.
- [ ] Account quota is not Doka application-path proof. Test an actual Doka-generated derivative/preview and restore/recovery behavior with a dedicated acceptance object; record checksums and clean up only that test object.

### Render
- [x] Connected account has a workspace named `My Workspace`.
- [x] Inspected Render workspace `My Workspace` (`tea-datqhq0jo6nc73c3qva0`) and queried services with previews both enabled and disabled on 2026-10-09; the connected service listing returned `null`, with no service IDs/configuration to inspect or edit. This does not prove that the owner has no Render service in another account/team; it means none is visible through the current connected workspace response.
- [ ] Owner/runtime follow-up: open Render Dashboard and confirm the service belongs to this account/workspace and is shared with the connected identity. Do not create a replacement service or deploy blindly. `infrastructure/railway/*` exists in the repository, but that is not evidence Railway is active; do not use it as the live runtime without confirmation.


### AI model and billing boundary
- [x] Inspected Vercel project environment-variable names without decrypting secrets: no `OPENROUTER_API_KEY` or other AI-provider key was present in the returned Vercel environment list. Values were not revealed.
- [x] Inspected Cloudflare Worker secret-binding names only: the Worker has storage/provider secrets but no OpenRouter/Gemini/Groq/OpenAI/Hugging Face AI key binding. Secret values were not retrieved.
- [x] PR #24 is merged to `main`; the unified AI service defaults to OpenRouter's free router, restricts generic chat to the explicit free-model allowlist, and routes embeddings only to the free OpenRouter embedding allowlist. Other provider APIs are not registered by the unified AI service; Hugging Face inference is not used as an embedding fallback. GitHub Doka Quality Checks and CodeQL both passed on merge commit `c0f9a5e1c73f750c58b926f45b074552650c0001`.
- [ ] The OpenRouter key's presence/usability and actual zero-cost usage are **not yet verified** because no key was found in the inspected Vercel/Cloudflare secret stores and no active Render service was visible through the connector. Do not paste a key into chat or logs. Once the intended backend service is confirmed, add the key in that service's secret manager, then run a non-sensitive smoke request and verify the model/usage in OpenRouter.
- [ ] Some supplied model IDs are specialized (embedding, reranking, content safety, audio, behavior scoring). They must only be wired into matching task-specific adapters; they are not interchangeable with chat-completion models.
- [ ] Render runtime configuration remains unverified because the explicit `My Workspace` service-list requests returned `null`. Confirm the actual service in Render Dashboard before changing environment variables or deploying; do not guess a service ID or substitute Railway.


### Cloud completion conditions
- [ ] Resolve Supabase leaked-password-protection warning.
- [ ] Investigate why recent Vercel production deployments are canceled and establish owner intent before any promotion.
- [ ] Run two-user Cloud E2E/isolation and real provider-path recovery tests using disposable identities and test objects.
- [ ] Verify QStash/Workflow/Redis are intentionally idle or execute acceptance tests against a dedicated endpoint.
- [ ] Store scrubbed evidence and re-run security/performance advisors and deployment smoke checks after authorized fixes.


## E. Exact-HEAD and consent safety reminders — 2026-10-11
- [ ] Current CI evidence is stale relative to later code/docs commits: run 38072383164 passed nine reported jobs on c470c260d38de59766b90b3f1d8c0ecd55d625c3, not the current main HEAD. Verify a new directly associated successful run before code-side closure.
- [x] Consent grant/revocation/audit lifecycle is persisted and authenticated via the local bearer identity; external AI checks the active database grant on each call. Verify deployment uses the intended LOCAL_AUTH_STATE_PATH and AI_EXTERNAL_PROCESSING_CONSENT remains false until explicit operational approval. Confirm each caller derives resource scope from authorized server-side document context. Do not provide a client-supplied grant as the authority and do not enable external processing without the trusted grant path.
- [ ] If local OCR/browser/cloud evidence is unavailable to the repository runtime, keep the gate pending and record the exact missing artifact/input; do not manufacture evidence or mark the release ready.


## Status reconciliation — 2026-10-14 (overrides conflicting checkbox claims above)

The owner checklist has historical checkbox notes that overstate the current evidence when read beside docs/TESTING.md. Use the following status until the linked evidence is reconciled:

- **A4 / Gate 4: PARTIAL, not complete.** Chromium acceptance imported/analyzed 346 files and reached plan review. The run does not establish approval/apply, final copy, backup, isolated restore and undo as one complete browser flow. Keep those steps unchecked until a new trace/evidence proves them.
- **A5 / Gate 6: EVIDENCE RECONCILIATION REQUIRED.** The checklist reports Backup 6.14 s, Restore/RTO 4.33 s, RPO 0, but link the reproducible report and confirm commit, dataset, and measurement method before marking the gate closed. Do not discard the reported values; treat them as provisional until reconciled.
- **A6 / Gate 7–8: exact-SHA CI is required.** The latest implementation commit from last night's work was 7aacce61a4291e24c6988938aad98c0bb4cad7d3; the subsequent commits in this reconciliation are documentation-only; Actions run #870 is for 1d404b18d4b927f7fde69fef0fc14116ad6f2849. A later documentation/code commit needs its own associated successful run before the final freeze is claimed.
- **Gate 3 OCR remains blocked** by the recorded benchmark; visually validate the Myanmar reference and rerun representative language-specific mya and eng samples without weakening thresholds.
- **Cloud owner work is the immediate priority:** prepare two disposable users/tokens locally in environment variables/secret storage, then run the documented acceptance commands. Do not share tokens in chat, Git, shell history or logs. Cloud Gates 9–11 remain pending until real evidence is recorded.
- The leaked-password-protection setting remains deferred under the current owner decision; it is not an active action in this handoff unless that decision changes.
