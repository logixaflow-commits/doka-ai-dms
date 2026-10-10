# Doka Current State

## 1. Current Release
**Evidence-gated Personal Local release preparation with Cloud verification in parallel.** No gate is upgraded without direct evidence.

## 2. Current Phase
**Release close-out — Gates 3–12.**

## 3. Overall Status
- **Personal Local:** foundation implemented; real OCR benchmark data, real browser acceptance, copied-office pilot, and measured recovery drill remain required.
- **Personal Cloud:** foundation implemented; authenticated lifecycle, two-user isolation, B2/Drive recovery and full provider-boundary evidence remain pending. The acceptance runner was reconciled to the current signed direct-upload/download contract, hashes actual downloaded bytes, records privacy-safe failure evidence and performs best-effort cleanup in a finally path; fresh CI/runtime evidence is still pending.
- **Enterprise:** deferred.
- **Cloudflare Worker:** current live deployment is verified below.
- **Vercel:** project reports `live=false`; the repository's Vercel production smoke workflow explicitly states production is intentionally paused and is manual-only. Keep Gate 12 blocked until owner-approved reactivation and final acceptance.
- **Render:** no services were returned for the connected Render workspace; this is evidence of no accessible active Render runtime.

## 4. COMPLETED
- Phase A–E remediation work preserved as historical evidence.
- Documentation migration Phases 1–6.
- Personal Local foundation.
- Personal Local pilot harness hardened in-repo: all source/workspace/backup/evidence paths must be disjoint; symlink roots, nested source symlinks, non-empty pilot roots and non-file evidence targets fail closed before processing. Source snapshot and symlink checks run before mutable roots are created. These checks have regression coverage.
- Local Auth/Session/Restart/Replay implementation.
- Organization Apply/locking/limits/Undo implementation.
- Dependabot/secret-scan/lockfile/lint reconciliation.
- Personal Cloud foundation.
- Cloudinary provider-level recovery probe: upload, backup download, delete, and post-delete placeholder verification.

## 5. VERIFIED
- Gate 1: local auth/session/restart/replay code and automated safety verification; browser acceptance remains separate.
- Gate 2: organization apply/locking/limits/undo automated verification; browser acceptance remains separate.
- Gate 7: quality/dependency/security workflow evidence is green.
- Live Supabase migration head: `20261009083942_doka_trigger_function_least_privilege` — applied during the 2026-10-09 cloud follow-up and verified from the live migration list. The corresponding migration filename is reconciled on PR #24.
- Trigger-function privilege verification after migration: `anon_can_execute=false`, `authenticated_can_execute=false`, `service_role_can_execute=true` for `public.doka_set_updated_at()`.
- Cloudflare Worker `doka-ai-dms` is live at 100% traffic; the latest inspected deployment is version 671 (100% on version ID `14e89790-c793-4d9b-9025-c5c7f412033f`). The configured 50 MiB limit and provider bindings are present; provider application-path acceptance remains pending. Production D1 `DOKA_DB` remains provisioned and bound; reviewed baseline migration is applied and disposable live idempotency/outbox acceptance passed.
- Render connected workspace `My Workspace`: explicit service-list calls returned `null` on 2026-10-09; no service ID/configuration was available to inspect. This is a connector visibility result, not proof no service exists in another account/team. Railway configuration files in the repository are not proof that Railway is the active runtime.
- Cloudinary provider-level recovery probe on 2026-10-08: 22-byte test object, SHA-256 42b68a292fea02d6220c0ee02a4489697758f19d4fb1420d9063697087583a1c; backup download returned exact payload; delete returned success; subsequent asset lookup returned a zero-byte placeholder, proving the original delivery object was removed. Tool-side duration was not exposed.

## 6. IN PROGRESS
- 2026-10-09 cloud checkpoint: live Supabase security advisor still has leaked-password protection WARN; latest inspected Cloudflare Worker version is 671 at 100% traffic. Supabase least-privilege trigger-function migration is now applied and verified. Neither observation closes application acceptance gates.
- Vercel project `enterprise-ai-dms` remains `live=false` with latest deployment `CANCELED`. The deployment API links the cancellation to the ignored-build-step setting, and `.github/workflows/vercel-production.yml` explicitly documents production as intentionally paused/manual-only. No production deploy was triggered; Gate 12 remains blocked pending owner-approved reactivation and gate evidence.
- Train 1 checkpoint: D1 job-idempotency/outbox adapters are now live-backed and their disposable acceptance evidence is recorded; AI retry/circuit/failover and OCR-aware retrieval remain runtime/provider evidence gates.
- Train 1 implementation status (2026-10-11 follow-up): durable job idempotency now has a Windows inter-process lock fallback and a Windows-lock regression test; the OCR benchmark now fails its gate when per-language CER/WER exceeds default thresholds (mean CER 0.30, mean WER 0.60); the active unified AI service now requires a granted subject + purpose + exact-resource scope for provider calls and embeddings. These code changes are not a release pass: GitHub Actions run 38072383164 passed all nine reported jobs on commit c470c260d38de59766b90b3f1d8c0ecd55d625c3, but that run predates the later consent-test commits at HEAD (8094733592ec9255a093d52610bdc0c9ee733d07), so CI for the exact current HEAD is not yet directly verified. End-to-end consent persistence/caller wiring is not yet proven, and real provider/runtime acceptance plus visually verified Myanmar/English OCR references remain outstanding. Human approval remains mandatory. Distributed worker takeover remains intentionally disabled.
- Train 1/3 hardening: workflow idempotency, D1 job idempotency, outbox retry/DLQ handling, AI circuit/failover/consent/schema boundaries, and OCR-aware retrieval safeguards are implemented; distributed worker takeover remains intentionally disabled.
- Live Supabase Security Advisor recheck on 2026-10-09 still reports `auth_leaked_password_protection` as WARN. The connected Supabase tool exposes no Auth security-setting mutation, so an authorized project operator must enable it and rerun the advisor; this remains a release/security-freeze blocker.
- Gate 3: OCR benchmark evidence reconciliation.
- Gate 4: synthetic Chromium browser flow now passes on 2026-10-09 (login → import → scan → understand → review plan; source SHA-256 unchanged), with privacy-safe evidence at `Phase0_Evidence/acceptance/personal-local-browser-smoke-2026-10-09.json`. Gate remains PENDING until the same flow is exercised with representative copied-office data and real OCR requirements.
- Gate 5: copied-office pilot and before/after source hashes.
- Gate 6: measured backup/restore RTO/RPO.
- Gate 9: authenticated Cloud lifecycle E2E.
- Gate 10: two-user isolation plus live RLS/Storage/API proof.
- Gate 11: B2 >50 MiB, Google Drive export/recovery, 50 MiB routing and complete provider recovery evidence.
- Release-gate hardening: Gate 12 now requires explicit `passed: true` final deployment/runtime sign-off in addition to Gates 8–11; regression tests are wired into Doka Quality Checks. GitHub Actions run 38072383164 confirms this workflow configuration and release-gate regression coverage passed on commit c470c260d38de59766b90b3f1d8c0ecd55d625c3; the exact current HEAD still needs a directly associated run before this line can be marked CI-verified.
- Final live-infrastructure evidence reconciliation.

## 7. PENDING
- Gate 3: BLOCKED/PENDING. The latest six-sample report is now correctly `gate_ready=false`: the Myanmar/English sample scored CER 79.94% and WER 171.43%, exceeding the benchmark defaults (mean CER ≤0.30 and mean WER ≤0.60). The OCR reference still requires visual verification against the rendered scan, and a representative re-run is required after correction. Do not use the older aggregate report to close this gate.
- Gate 4: the Playwright flow ran successfully in headless Chromium against a local Personal Local backend/frontend with one synthetic text file. It covered login, import, scan, understand/OCR action, review plan and source hash equality. This is a smoke pass, not representative-office release evidence; Gate 4 remains pending.
- Gate 5: pilot harness and source-hash logic exist; path-overlap, symlink and isolated-root safety are now regression-tested. Only synthetic evidence is recorded. No copied representative office-data pilot has been run in this pass.
- Gate 6: synthetic backup/restore evidence exists; no timed real-machine drill was run, so RTO/RPO are unmeasured.
- Gate 9: live Worker unauthenticated probe returned HTTP 403; no disposable authenticated test-user session was available for the required lifecycle test.
- Gate 10: live Supabase is healthy with current migrations, but two real authenticated test users were not available. Existing synthetic RLS probes are not accepted as two-user release evidence.
- Gate 11: Cloudinary provider-level recovery verified; B2 and Google Drive live credentials/connectors are not available. Therefore the complete storage/recovery gate remains PENDING.
- Vercel production pause: repository workflow documentation explicitly says production is intentionally paused and its smoke workflow is manual-only. The latest deployment was canceled by the ignored-build-step setting; do not infer a failed app build or reactivate production without owner approval.
- Cloudflare deploy workflow: the old duplicate `Doka Cloudflare Deploy` workflow repeatedly failed at `setup-node@v7` before deployment/health checks and used unpinned `wrangler@latest`. PR #24 removes that workflow in favor of the retained pinned, dry-run, explicit-confirmation `Cloudflare Worker Production Deploy` path.

## 8. BLOCKED
- AI billing guard is merged to `main` in PR #24: the unified service is restricted to allowlisted OpenRouter free chat models and free embeddings; billable provider adapters and Hugging Face inference are not registered/called. GitHub Doka Quality Checks and CodeQL passed on merge commit `c0f9a5e1c73f750c58b926f45b074552650c0001`. This is repository/CI verification, not proof that a deployed runtime has the key configured or has made a zero-cost inference request.
- OpenRouter credential reachability is unverified: no AI provider key name was found in the inspected Vercel environment list or Cloudflare Worker secret bindings. No test inference request was sent and no key value was read. Confirm the intended backend runtime/secret store before claiming the key works.
- Gate 8: Personal Local final freeze, blocked until Gates 1–7 are fully evidenced.
- Gate 12: deployment/final go-live, blocked until Gates 9–11 are fully evidenced.

## 9. DEFERRED
- Enterprise edition and enterprise RBAC.
- Phase 7/8 activation evidence and production runtime validation.
- Phase 9–18 future expansion tracks.
- Cloud-first approaches preserved in archive as historical material.

## 10. REMAINING RELEASE GATES
| Gate | Status |
|---|---|
| 1 Local auth/session/restart/replay | Implemented / automated verified; browser pending |
| 2 Organization Apply/locking/limits/Undo | Implemented / automated verified; browser pending |
| 3 OCR limits + Myanmar/English benchmark | PENDING |
| 4 Personal Local browser E2E | PENDING |
| 5 Copied-office pilot + source hashes | PENDING |
| 6 Backup/restore + measured RTO/RPO | PENDING |
| 7 Dependabot/secret/lockfile/lint | VERIFIED |
| 8 Personal Local final freeze | BLOCKED |
| 9 Cloud authenticated E2E | PENDING |
| 10 Two-user isolation + RLS | PENDING |
| 11 Storage provider/recovery + 50 MiB | PENDING |
| 12 Deployment/runtime + final sign-off | BLOCKED |

## 11. LAST VERIFIED
- Disposable runtime checkpoint 2026-10-09: Python 3.13, Node 24.21.0 (installed through an isolated npm runtime), npm 10; required maintained backend modules available; Tesseract absent; Cloud acceptance tokens absent. Acceptance preflight returned not-ready without recording secrets.
- 2026-10-09 targeted Cloud storage/provider/D1 migration acceptance suite: 90 passed in a disposable Python 3.13 runtime, including signed upload/download integrity and release-gate regression tests. The maintained Personal Local backend suite also passed 58 tests. This is local targeted evidence, not a verified GitHub Actions result. The broad legacy backend directory still has five collection errors in deferred ORM/model tests; no broad-suite pass is claimed.
- 2026-10-09 dependency audit: pip-audit reports parsed for all six backend profiles (`requirements.txt`, production, local, dev, test, cloud) and the root `pyproject.toml`; each report contains zero unignored vulnerability findings. The backend scan retains the workflow’s existing explicit ignore for `PYSEC-2025-183`; this is local audit evidence, not a replacement for the latest GitHub Actions run.
- D1 authorization migration 0002 applied to production D1 on 2026-10-09 after a completed SQL export (8,910 bytes; SHA-256 and bookmark recorded in `Phase0_Evidence/train1/d1-authorization-migration-2026-10-09.json`) was restored successfully into disposable SQLite. All 5 relevant metadata tables were empty before the change. Post-apply read-only verification found all 7 expected authorization index/trigger objects and confirmed those tables remain empty; 4 disposable SQLite migration tests pass.
  Important boundary: the active Cloud document API still uses Supabase Postgres/Storage; these D1 guards harden the provisioned D1 schema only and do not substitute for live Supabase RLS plus two-user API acceptance.
- Workflow targeted runtime checkpoint 2026-10-08: 6/6 workflow contract tests passed in the disposable runtime after idempotency/locking hardening. Full backend suite was not rerun.
- Durable job idempotency contract: claim/state/attempt persistence, retry exhaustion, DLQ transition and concurrent duplicate claims are now covered by focused contract tests; no queue takeover is enabled.
- Maintained backend regression suite: 386 passed in the latest recorded full run; the full maintained suite was not rerun in this pass. The separate targeted Cloud suite result is recorded above.
- Frontend 2026-10-09: `npm ci`, production TypeScript/Vite build, all smoke tests, ESLint and `npm audit --audit-level=high` passed under Node 24.21.0; npm reported zero vulnerabilities. Playwright discovery found one test; actual browser acceptance remains pending because authenticated pilot credentials, representative source data and Tesseract are unavailable.
- Quality + CodeQL evidence: latest recorded workflow run passed.
- Live Supabase head: 20261005113241_doka_audit_export_backup_actions, freshly verified on 2026-10-08.
- Cloudflare Worker: latest inspected version 652 at 100% traffic on 2026-10-09; no rollback or traffic change was performed.
- Render: connected workspace returned no services.
- Cloudinary: provider-level recovery probe passed on 2026-10-08 as recorded above.
- Vercel: project inactive/latest production deployment canceled; explicit paused flag unavailable.

## 12. NEXT ACTION
**Owner-provided runtime evidence is now the critical path.** The repository is prepared through Gates 3–11: Personal Local OCR/pilot/browser/recovery runners are ready, and `scripts/cloud_acceptance.py` now uses the current signed direct-upload/completion contract, verifies actual downloaded bytes, and is ready for Gate 9/10 execution after CI validation with two pre-created user access tokens plus an exact 50 MiB fixture. Gate 11 still requires live B2 and Google Drive credentials/connectors and a real Cloudinary application-path run. Then rerun only the blocked gates, record measured evidence, and close Gate 8 before Gate 12.

- Train 1 safety contracts are now wired into concrete paths where the repository has them: D1 jobs/outbox, unified AI provider routing, and vector retrieval. Remaining evidence is runtime/provider acceptance; no concrete queue consumer exists in the current Worker, and production D1 is provisioned and bound to the Worker; no queue consumer is exposed by the current Worker entrypoint.


## 13. TRAIN 1 CONCRETE INTEGRATION CHECKPOINT — 2026-10-08
- Durable D1 job adapter: implemented in cloudflare_worker/jobs.py against the existing jobs table schema (unique idempotency_key, bounded attempts, terminal success/dead states). No lease takeover is enabled.
- Outbox: actual delivery failures now use a conservative retry taxonomy; permanent failures dead-letter immediately and transient failures use bounded backoff.
- AI: unified_ai_service now uses the Train 1 circuit breaker and retry taxonomy; provider failover is opt-in via AI_PROVIDER_FAILOVER_APPROVED and structured/non-retryable failures fail closed.
- Retrieval: vector_search now canonicalizes OCR text to Unicode NFC, validates mya/eng identity + SHA-256, scopes ranking by language, and uses deterministic local ranking for Myanmar OCR instead of the English-centric embedding model.
- Runtime constraint: D1 runtime acceptance is now PASS for the disposable ledger/outbox state-transition scope. Provider runtime evidence and Myanmar/English benchmark remain pending.


## 14. TRAIN 1 CI RECONCILIATION — 2026-10-08
- Concrete Train 1 implementation is CI-verified on main: Doka Quality Checks passed and CodeQL passed on the final implementation commit 06f6874aa999fec441bbb285327a17af795625c2.
- The Quality run covered backend regression (including Train 1 safety/AI/retrieval tests), Cloudflare job/outbox/storage contracts, dependency audits, static/SBOM checks, frontend lint/build/smoke, and symlink security.
- This closes the implementation/CI portion of Train 1. D1 runtime infrastructure and disposable ledger acceptance are now closed; real OCR tooling, browser data, authenticated cloud users, provider recovery, and AI provider runtime evidence remain open.


## 15. TRAIN 1 RUNTIME EVIDENCE STATUS — 2026-10-08
- Concrete integration remains CI-verified: latest Doka Quality Checks **SUCCESS** and CodeQL **SUCCESS** on commit `ce328544a1b88b32fb53bd01227789bcbf3446a0`.
- Live Cloudflare Worker is version 652 at 100% traffic (verified 2026-10-09).
- Cloudflare direct-upload session signing uses a dedicated `DOKA_STORAGE_SESSION_SECRET` Worker secret; `DOKA_SINGLE_USER_EMAIL` remains enabled for the current single-user deployment.
- Live D1 is now provisioned, migrated and bound to the Worker. Disposable acceptance passed duplicate convergence, terminal success, retry exhaustion/dead transition and outbox terminal delivery; privacy-safe evidence is recorded at `Phase0_Evidence/train1/d1-job-runtime.json`.
- Supabase Auth leaked-password protection remains a security-freeze blocker.
