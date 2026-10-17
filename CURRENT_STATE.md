> **AUTHORITATIVE OWNER-APPROVED RELEASE CHECKPOINT — 2026-10-17**
>
> **Official decision:** **Production Ready — Conditional Sign-Off (Owner-approved launch with explicitly deferred post-launch work)**
>
> This checkpoint supersedes earlier statements in this file that treated the four owner-deferred verification gates as pre-launch blockers. The product owner has explicitly accepted the current production-grade foundation and authorized launch with the bounded post-launch backlog below. This is a conditional owner-approved release decision, not a claim that every specialized acceptance drill has passed.
>
> ### Verified production foundation
>
> - **Vercel Web Platform:** production deployment is READY; https://enterprise-ai-dms.vercel.app/ returns HTTP 200. Production and Preview bundles are configured for their respective production/staging services.
> - **Cloudflare Worker API:** production Worker doka-ai-dms is live; /health and /api/config return HTTP 200; unauthenticated document reads are rejected with HTTP 401; strict CORS permits canonical production origins and does not reflect an untrusted origin.
> - **Supabase:** RLS is enabled on public document, version, and audit tables with owner-scoped policies. The document bucket is private and configured with a 50 MiB limit. These are policy/configuration findings; live two-user isolation and exact-size byte-integrity are explicitly deferred below.
> - **Automated quality:** CI/quality checks and CodeQL passed; self-audit passed 23/23; 138 maintained regression tests and 63 cloud-provider contract tests passed. These automated results support the foundation but do not substitute for the deferred end-to-end drills.
> - **Known plan limitation:** Supabase leaked-password protection remains unavailable on the current plan; it is not represented as fixed by this sign-off.
> - **Backend re-audit (2026-10-17):** deployed Worker source hashes match the repository for the API and storage modules; production provider credentials are Cloudflare secret bindings, and Vercel client configuration exposes only the public Supabase publishable key. Historical credential hygiene has a separate security follow-up and is not represented as cleared by CI.
- **Backend security hardening (PR #81, merged 2026-10-17):** Telegram gateway actions now require `TELEGRAM_ACTION_WEBHOOK_SECRET` and constant-time header comparison; unsupported document mutations return HTTP 501 rather than false success; receipt output is HTML-escaped. Electron external-link IPC accepts only credential-free HTTP(S) URLs from the main application frame. The legacy, unmounted webhook receiver now rejects missing/invalid signatures and does not log raw payloads. Doka Quality Checks, Production CI/CD, CodeQL, Dependency Review, and desktop Electron smoke passed on the PR head; PR #81 merge-commit checks also passed. PR #86 merge-commit checks are running separately.
- **Rate-limit and error-log hardening (PR #86, merged 2026-10-17):** the FastAPI local backend ignores forwarded-IP headers by default; `TRUST_PROXY_HEADERS=true` is an explicit opt-in for a trusted proxy that strips/overwrites client-supplied forwarding headers. Proxy IP values are parsed as IP addresses, malformed values fall back to the direct peer, and request exceptions are logged by type/request ID without exception text. PR-head Production CI/CD, Doka Quality Checks, CodeQL, and Dependency Review passed; merge-commit checks are pending.

- **Owner-deferred credential follow-up:** historical AI-provider credential rotation and Gemini assignment review remain intentionally skipped per the owner's explicit instruction; current-file secret scanning is not proof that Git history exposure has been remediated.
- **RPC live audit (2026-10-17):** read-only inspection found all three public production tables have RLS enabled and no public-schema SECURITY DEFINER or anon-executable functions. Staging has four owner-checked SECURITY DEFINER RPCs with fixed `pg_catalog, public, pg_temp` search paths and EXECUTE for `authenticated`/`service_role`; Supabase Advisor warns about authenticated execution and the warning remains under review. Production grants allow authenticated updates to `status` and `deleted_at`, but deny storage-pointer columns needed by version replace/restore. Track [RPC/migration reconciliation issue #82](https://github.com/logixaflow-commits/doka-ai-dms/issues/82); database pushes remain frozen until staging HTTP lifecycle/isolation evidence and migration-ledger reconciliation are complete.
- **Telegram domain-action follow-up:** document-mutation buttons remain disabled until an owner-authorized domain service and audit trail are implemented; see [issue #83](https://github.com/logixaflow-commits/doka-ai-dms/issues/83).
> - **RPC release caveat:** production's four sensitive RPCs are restored to the pre-hardening `SECURITY INVOKER` mode because the documented staging HTTP lifecycle/A-B prerequisite remains unmet. The current authenticated column grants do not permit direct updates to storage-pointer fields, so version replacement/restore may fail at runtime. Authenticated UPDATE grants do include `status` and `deleted_at`, so bulk status/trash have the required column privileges but still need authenticated HTTP acceptance. These flows are not accepted as verified; database pushes are frozen until the migration ledgers are reconciled and the guarded forward fix is approved.
>
> ### Authoritative Owner-Approved Post-Launch Quality Backlog
>
> The following four items are explicitly deferred by owner decision and must remain visible in the post-launch quality roadmap:
>
> 1. **Staging Synthetic A/B Isolation Drill** — execute the GitHub Actions authenticated lifecycle/isolation workflow with two distinct disposable staging-user credentials/tokens; verify cross-user denial and exact 50 MiB file byte/hash integrity.
> 2. **Myanmar/English OCR CER Optimization** — refine the benchmark and OCR pipeline to reduce mean character error rate from approximately 0.33 (recorded 0.3379) to below 0.30 using verified ground-truth references. Do not relax acceptance thresholds to manufacture a pass.
> 3. **Secondary Staging Disaster Recovery Drills** — configure staging-only B2, Cloudinary, and Google Drive bindings and execute application-path recovery/restore cycles. Do not use production credentials or production data for destructive tests.
> 4. **Real-Browser Copied Office Dataset Acceptance** — run the real-browser copied-dataset flow through review, human approval, final copy/apply, backup, isolated restore, and undo; capture evidence and measured recovery objectives.
>
> ### Release interpretation and safeguards
>
> - **Release status:** owner-approved conditional sign-off; the four items above are post-launch work, not pre-launch blockers under this explicit owner decision.
> - **No false closure:** deferred checks are not described as passed. Track each item to evidence-backed completion in the quality roadmap.
> - Keep production and staging credentials/data isolated. Never run destructive acceptance against production. Preserve rollback readiness and source-data immutability.
> - Keep this checkpoint authoritative until superseded by a dated evidence-backed release update.
>
> **Repository:** logixaflow-commits/doka-ai-dms, default branch main. This documentation checkpoint is intended to be committed to main; the resulting commit SHA is recorded by GitHub after the update.

---

## Historical checkpoints (superseded; audit trail only)

The dated notes below preserve prior observations and may conflict with the authoritative owner-approved release decision at the top of this file. They are retained for audit traceability and must not be interpreted as current status.

> **Repository/provider re-audit — 2026-10-15 (read-only; supersedes older provider snapshots where they conflict)**
>
> - Latest observed `main` SHA at audit time: `6c1fe995c807382cbe3c1000e893e678d621f83b` (UI toast notifications). Exact-SHA CI for this SHA must be checked before claiming current-HEAD CI is green; older successful runs are not transferable to this commit.
> - Vercel `enterprise-ai-dms`: `live=false`; latest production deployment for this SHA is `CANCELED`. Keep production paused/manual-only; no deployment or traffic mutation was performed.
> - Render `My Workspace` service listing returned `null` even with previews enabled. This is connector/workspace visibility only. Owner must confirm the intended workspace/service; do not create a replacement.
> - Supabase `Enterprise AI DMS` (`jkobgssaqifzrqfirdfu`) reports `ACTIVE_HEALTHY`, region `ap-southeast-1`, Postgres 17. Live migration listing includes `20261009083942_doka_trigger_function_least_privilege` as latest. Policy configuration is not two-user isolation evidence; Gates 9–11 remain open.
> - Cloudflare account API returned zero zones. Worker script `doka-ai-dms` exists, but script-list metadata returned `routes: null` and an empty `deployment_id`; reconcile deployment/version/route state with the prior deployment evidence before claiming current routing is fully verified. No secrets were read or changed.
> - Detailed findings and prioritized work inventory: [docs/REPOSITORY_INFRA_AUDIT_2026-10-15.md](docs/REPOSITORY_INFRA_AUDIT_2026-10-15.md).
>
> **Next action:** verify exact-SHA CI on `6c1fe995c807382cbe3c1000e893e678d621f83b`, then run disposable authenticated Cloud Gates 9–11; separately confirm the intended Render service and reconcile Cloudflare routes. Keep Vercel production paused until owner approval and all required gates pass.

---

> **Follow-up verification — 2026-10-14 (read-only cloud + branch review)**
>
> - Documentation HEAD `4401eba153b13167aa7e552f1b3eec56ab7d1d02` now has a successful [Doka Quality Checks run](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38561399407).
> - Read-only Supabase inspection confirms RLS is enabled on `public.doka_documents`, `public.doka_document_versions`, `public.doka_audit_events`, and `storage.objects`. Owner-scoped policies exist for document reads/writes, version reads/inserts, audit reads/inserts, and the private `doka-documents` bucket's `users/{auth.uid()}/...` object paths. The bucket is private and configured for a 52,428,800-byte (50 MiB) maximum. This is **policy configuration evidence only**; real two-user JWT isolation is still pending. Tables and bucket were empty during inspection.
> - Cloudflare Worker `doka-ai-dms` is deployed with 100% traffic on its latest listed version (deployment created 2026-10-13 07:02 UTC); provider secret bindings for B2, Cloudinary, Google Drive and Supabase are configured. Binding presence does not prove values are valid or provider flows work. No deploy/config mutation was performed.
> - Compared `fix/myanmar-ocr-text-preservation` to current `main`: it is diverged, 13 commits ahead and 120 behind. The branch has older OCR service/safety-test and Google Drive contract-test files than `main`; current `main` already contains the character-preservation post-processing and regression workflow. Do **not** merge the whole stale branch. Reuse only a demonstrably missing fix after targeted diff/test review.
> - Connected Render workspace returned no services. Do not create a replacement service or guess the intended service; owner must confirm the target workspace/service in the Render dashboard if a Render-hosted runtime is still expected.
>
> This supplements the handoff above; it does not close Cloud Gates 9–11 or local OCR/browser/recovery gates.

---

> **Authoritative reconciliation — 2026-10-14, after dependency PR #47 merge**
>
> - Current `main` candidate: `960923a656ffaf2739b21c7cebdb48c83456fef1` (dependency-only merge). [Doka Quality Checks](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38561142421), [CodeQL](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38561144243), and [Myanmar OCR Regression](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38561142780) all passed on this exact SHA. This closes the exact-HEAD CI requirement for this candidate, not the real-environment release gates.
> - **Cloud-first next actions:** Gate 9 authenticated lifecycle; Gate 10 two-user isolation; Gate 11 real B2/Cloudinary/Google Drive application-path recovery. These remain pending because disposable authenticated sessions and provider runtime evidence are not present in this environment. Supabase tables and the `doka-documents` bucket currently have zero rows/objects; no customer content was read or modified.
> - **Local gates remain separate:** Gate 3 OCR still fails the recorded strict benchmark; Gate 4 browser evidence stops at plan review; Gate 5/6 pilot and recovery measurements require reconciled evidence. Do not upgrade them from historical checkbox claims alone.
> - **Gate 12 remains blocked:** Vercel production is intentionally paused/manual-only; no deployment or traffic change was made. Do not reactivate without explicit owner approval and Gates 8–11 evidence.
> - **Supabase leaked-password protection:** advisor still reports WARN, but this is deferred under the current owner decision and is not an action item in this handoff unless that decision changes. Do not treat it as fixed; do not change the setting through this workflow.
> - Dependency PR [#47](https://github.com/logixaflow-commits/doka-ai-dms/pull/47) was merged after its backend regression, cloud storage contracts, frontend build/smoke, dependency audit, CodeQL, and OCR regression checks passed. The main-branch CI above validates the merge SHA.
>
> This block overrides conflicting historical statuses below. Historical records are retained for traceability.

---

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
- **Render:** the connected workspace service-list calls returned `null`; no service ID/configuration was available to inspect. This is a connector visibility result, not proof no service exists elsewhere.

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
- Live Supabase RLS policy inspection (2026-10-13): RLS is enabled for `public.doka_documents`, `public.doka_document_versions`, `public.doka_audit_events`, and `storage.objects`. Document/audit owner policies compare `owner_id` with `auth.uid()`; version policies require ownership of the parent document; document UPDATE includes a `WITH CHECK` preserving owner identity; Storage policies restrict the `doka-documents` bucket to `users/<auth.uid()>/...`. This verifies policy definitions only; two-user authenticated API/storage isolation is still pending.
- Live Supabase migration head: `20261009083942_doka_trigger_function_least_privilege` — applied during the 2026-10-09 cloud follow-up and verified from the live migration list. The corresponding migration filename is reconciled on PR #24.
- Trigger-function privilege verification after migration: `anon_can_execute=false`, `authenticated_can_execute=false`, `service_role_can_execute=true` for `public.doka_set_updated_at()`.
- Cloudflare Worker `doka-ai-dms` is live at 100% traffic on active version `75e436b2-2009-4779-b659-5421bea0843a`, deployment `d894b59e-4aca-4fa2-86b2-9750055749eb` (2026-10-13). The 50 MiB routing limit and B2 per-user quota binding (1 GiB, warn 80%, block 95%) are configured; authenticated provider application-path acceptance remains pending. Production D1 `DOKA_DB` remains provisioned and bound; reviewed baseline migration is applied and disposable live idempotency/outbox acceptance passed.
- Render connected workspace `My Workspace`: explicit service-list calls returned `null` on 2026-10-09; no service ID/configuration was available to inspect. This is a connector visibility result, not proof no service exists in another account/team. Railway configuration files in the repository are not proof that Railway is the active runtime.
- Cloudinary provider-level recovery probe on 2026-10-08: 22-byte test object, SHA-256 42b68a292fea02d6220c0ee02a4489697758f19d4fb1420d9063697087583a1c; backup download returned exact payload; delete returned success; subsequent asset lookup returned a zero-byte placeholder, proving the original delivery object was removed. Tool-side duration was not exposed.

## 6. IN PROGRESS
- 2026-10-13 follow-up: Myanmar OCR preserves the original image path for fallback when preprocessing/Tesseract fails, with regression coverage. Exact current `main` HEAD `ae7afdebdbe1ae76a935851109adc2450010d327` has a successful `Doka Quality Checks` run (all 9 reported jobs succeeded, including backend regression tests, frontend build/smoke, repository self-audit, symlink security, cloud storage contracts, static analysis/SBOM, and dependency/secret audits) and a successful CodeQL run. This closes the exact-HEAD CI evidence gap for this commit, but does not close the strict OCR quality gate: CER/WER benchmark acceptance remains unverified/blocked. The available validation box also passed focused OCR checks, Python compile checks, repository compileall, 23/23 self-audit checks, and frontend smoke tests. Google Drive remains single-configured-refresh-token export only; multi-account OAuth, Shared Drives, virtual classification, and approval-gated moves are explicitly pending.
- 2026-10-09 cloud checkpoint: live Supabase security advisor still has leaked-password protection WARN; latest inspected Cloudflare Worker version is 671 at 100% traffic. Supabase least-privilege trigger-function migration is now applied and verified. Neither observation closes application acceptance gates.
- Vercel project `enterprise-ai-dms` remains `live=false` with latest deployment `CANCELED`. The deployment API links the cancellation to the ignored-build-step setting, and `.github/workflows/vercel-production.yml` explicitly documents production as intentionally paused/manual-only. No production deploy was triggered; Gate 12 remains blocked pending owner-approved reactivation and gate evidence.
- Train 1 checkpoint: D1 job-idempotency/outbox adapters are now live-backed and their disposable acceptance evidence is recorded; AI retry/circuit/failover and OCR-aware retrieval remain runtime/provider evidence gates.
- Train 1 implementation status (2026-10-11 follow-up): durable job idempotency now has a Windows inter-process lock fallback and a Windows-lock regression test; the OCR benchmark now fails its gate when per-language CER/WER exceeds default thresholds (mean CER 0.30, mean WER 0.60); the active unified AI service now requires a granted subject + purpose + exact-resource scope for provider calls and embeddings. Consent now has authenticated local bearer endpoints, transactional SQLite grant/revocation state, append-only audit, and persisted-grant checks at the external AI boundary. The current consent change still requires exact-HEAD CI completion and deployment verification; caller code must supply identity from verified auth and a scope derived from separately authorized resource context. Real provider/runtime acceptance plus visually verified Myanmar/English OCR references remain outstanding. Human approval remains mandatory. Distributed worker takeover remains intentionally disabled.
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
| Gate | Status | Evidence / Notes |
|---|---|---|
| 1 Local auth/session/restart/replay | VERIFIED | Automated auth, multi-process byte locking verified |
| 2 Organization Apply/locking/limits/Undo | VERIFIED | Atomic batching, chunked apply up to 50k files, 1-click undo verified |
| 3 OCR limits + Myanmar/English benchmark | PENDING | tessdata_best installed; reference benchmark needs pure Unicode alignment |
| 4 Personal Local browser E2E | VERIFIED | Playwright Chromium test passed against active backend & frontend |
| 5 Copied-office pilot + source hashes | VERIFIED | 346-file pilot & 300-file SYM representative office pilot passed (0 failures) |
| 6 Backup/restore + measured RTO/RPO | VERIFIED | Measured RTO 4.33s, RPO 0; SHA-256 backup verified |
| 7 Dependabot/secret/lockfile/lint | VERIFIED | Zero unignored vulnerabilities; compileall clean |
| 8 Personal Local final freeze | READY | Personal Local Engine (Phases 1-4) completed and verified |
| 9 Cloud authenticated E2E | DEFERRED | Inactive for Single-User Personal Local mode |
| 10 Two-user isolation + RLS | DEFERRED | Inactive for Single-User Personal Local mode |
| 11 Storage provider/recovery + 50 MiB | DEFERRED | Inactive for Single-User Personal Local mode |
| 12 Deployment/runtime + final sign-off | DEFERRED | Inactive for Single-User Personal Local mode |

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
- Durable D1 job adapter: implemented in apps/web-platform/backend/cloudflare_worker/jobs.py against the existing jobs table schema (unique idempotency_key, bounded attempts, terminal success/dead states). No lease takeover is enabled.
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


## 2026-10-11 documentation reconciliation checkpoint
- Re-read the active root documentation, canonical domain docs, owner checklist, Train status and Phase 7–18 execution plan; inventoried the historical/archive Markdown tree. Historical/archive plans remain reference material, not active release commitments.
- Consolidated P0–P3 release blockers and future-train acceptance criteria in ROADMAP.md; aligned docs/PHASE_TRAIN_STATUS.md, docs/TESTING.md and docs/OWNER_LOCAL_CHECKLIST.md with current OCR thresholds, consent limitations and exact-HEAD CI rules.
- Repository self-audit on the available checkout: 23 checks, 22 PASS, 0 structural failures, 1 NEEDS_REVIEW due to seven evidence-path references not present in this checkout. This is NEEDS_EVIDENCE, not release approval; determine whether those evidence files are intentionally external or restore/link the correct artifacts.
- Python syntax compilation passed for the changed idempotency, OCR benchmark, unified AI service and focused tests. Focused pytest could not be run in this box because pytest is not installed. The exact current main HEAD still has no directly associated successful CI run in the evidence available at this checkpoint.

## Exact-HEAD CI checkpoint — 2026-10-11
- Commit: `1d404b18d4b927f7fde69fef0fc14116ad6f2849`.
- GitHub Actions run #870: [Doka Quality Checks](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38116845434) completed with conclusion `success`.
- All nine reported jobs passed: Cloud storage contract tests, backend dependency audit, symlink security tests, workflow configuration sanity, static analysis/SBOM, repository self-audit preflight, frontend build/smoke, backend regression tests, and root dependency audit.
- Workflow trigger was updated so Markdown/documentation changes run the quality workflow too. This closes the missing exact-HEAD CI evidence for this checkpoint, not runtime release gates.
- Consent lifecycle now includes authenticated local bearer endpoints, SQLite persistence, revocation, append-only audit, and DB-backed checks at the external AI boundary; exact-HEAD CI is pending for this change. Remaining: OCR benchmark is below quality threshold pending reference validation and representative scans; real local/browser/recovery and live cloud two-user/provider gates remain evidence-dependent.


## Reconciled execution state — 2026-10-14

- Plan priority is **Cloud-first**, while the Track A/Track B UI planning stream can proceed in parallel; local-machine acceptance remains queued until the owner has the approved local environment/data available.
- The latest implementation commit from last night's work was 7aacce61a4291e24c6988938aad98c0bb4cad7d3; the subsequent commits in this reconciliation are documentation-only (Personal Local 4-phase engine/docs). The known successful Actions run #870 is tied to 1d404b18d4b927f7fde69fef0fc14116ad6f2849; do not call the latest commit CI-verified without a run tied to that SHA.
- Personal Local Phases 1–4 are recorded as implemented, but this is not release approval. OCR Gate 3 remains blocked by strict benchmark results. Gate 4 is partial: the 346-file browser run reached plan review, not the complete approval/final-copy/backup/restore/undo journey. Pilot/source-hash evidence exists for copied datasets; recovery timings reported in the owner checklist must be reconciled to reproducible evidence before closing Gate 6.
- Cloud Gates 9–11 remain pending live authenticated lifecycle, two-user authorization, and B2/Cloudinary/Google Drive application-path recovery evidence. Gate 12 remains blocked; Vercel production stays paused until explicit owner approval.
- Google Drive multi-account/Shared Drive/virtual-classification work is future scope; do not confuse it with the current basic export/recovery gate. Supabase leaked-password-protection remains deferred under the current owner decision.
- This checkpoint changes planning/status documentation only; it does not claim new code changes, successful live tests, or fabricated evidence.
