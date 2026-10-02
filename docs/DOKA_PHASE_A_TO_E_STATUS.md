# Doka Phase A–E Delivery Gate

This document is the working acceptance boundary for the Doka Personal Local Edition. Changes are applied directly to main; no feature branch is required for this local-first workflow.

## Phase A — Security hardening
- Local authentication requires an explicitly configured bootstrap password.
- Repeated local login failures are rate-limited/locked out.
- Access and refresh tokens are type-checked.
- Original source is read-only; source-write mode is rejected.
- SOURCE_ROOT and WORKING_ROOT overlap is rejected.
- FINAL_ROOT and QUARANTINE_ROOT must remain inside WORKING_ROOT.
- BACKUP_ROOT must not be inside the working/source roots.
- Workspace file access validates session IDs, relative paths, and SHA-256 integrity.
- Backup restore rejects unsafe archive paths.
- Optional Sentry telemetry is scrubbed of request bodies, cookies, non-allowlisted headers, URLs/query strings, exception messages, stack-frame locals/source paths, log messages, tags, breadcrumbs, contexts, and user identity.
- AI remains disabled by default.
- Production API workspace routes verify Supabase Auth access tokens; local password authentication is disabled when ENVIRONMENT=production.

Acceptance: automated regression tests remain green for authentication, path security, manifest integrity, backup/restore safety, AI-disabled behavior, and telemetry scrubbing.

## Phase B — Local workflow usability
The supported flow is Import → SHA-256 verify → Scan → Read/OCR → Review plan → Human approval → Copy to Final → Backup/Undo.
- Resumable import sessions.
- Inventory and duplicate/collision reporting.
- Explicit review-only handling.
- Preview/download from the verified working copy.
- Explicit approval before Final organization.
- Copy-only organization with no overwrite of different content.
- Audit journal and safe undo.
- Workspace backup and recovery-only restore.
The original source is never the organization target.

## Phase C — OCR and search quality
- Local PDF/image OCR.
- English + Myanmar OCR environment validation.
- DOCX/XLSX/XLSM local extraction.
- Deterministic metadata extraction.
- OCR review UI and sidecar OCR corrections that do not mutate the document.
- Filename/path/text search with extension/category/review filters.
- Local-rule processing without AI.
The remaining quality gate is empirical: run representative Myanmar/English files on the real machine and record extraction failures and false classifications.

## Phase D — Real-world pilot and tuning
Phase D cannot be honestly marked complete from repository tests alone.

Use: python scripts/doka_pilot_check.py --source <COPY_OF_REAL_OFFICE_DATA> --require-ocr

The pilot gate hashes the supplied source copy before processing, imports and verifies a separate working copy, scans inventory and duplicate/collision groups, runs local document understanding/OCR, builds the organization review plan, creates a workspace backup, verifies the backup SHA-256, restores it into an isolated recovery directory and compares the restored file manifest, hashes the source copy again, and fails if the source changed or recovery verification fails.

Optional organization testing is explicit: python scripts/doka_pilot_check.py --source <COPY_OF_REAL_OFFICE_DATA> --require-ocr --apply-safe
Only proposals already classified as suggest_move are applied by that optional flag. Review/duplicate/version proposals are never auto-approved.

Pilot evidence to record:
- source file count and before/after source hash manifest;
- import verified/failed counts;
- OCR availability and representative Myanmar/English results;
- exact duplicate and likely-version false positives;
- organization proposals accepted/rejected;
- backup SHA-256, archive verification, restored-file manifest match, and recovery result;
- browser workflow result;
- regression fixtures added after tuning.

Phase D release gate: representative real-machine validation passes without source mutation and without unexplained organization changes.

## Phase E — Future enterprise/cloud architecture
Phase E is intentionally architecture-only until Phase D passes.
- Local filesystem + local SQLite/workspace remain the Personal Local data plane.
- React/Vite remains the web UI.
- Vercel now hosts the React/Vite UI; Speed Insights is integrated.
- Supabase Auth now provides the production browser login/session and the API verifies those sessions when Supabase is configured.
- Live Supabase project now has `public.doka_documents`, `public.doka_document_versions`, a private `doka-documents` Storage bucket (50 MiB per-object cap), owner-scoped RLS policies, and Storage path policies. Doka Storage grants select/insert/delete only; the unused object-update policy was removed because uploads use `x-upsert=false`. Nine Doka migrations are applied and verified against the live project. Authenticated users can update only document `status`, `metadata`, `filename`, `folder_path`, and `deleted_at`; object keys, hashes, and ownership are not updateable through table grants.
- Live Supabase least-privilege audit found default grants giving `anon` broad table privileges and `authenticated` unnecessary update/delete privileges on the Doka tables, despite RLS. Applied migration `20261001100118_doka_least_privilege_grants` and `20261001100500_doka_storage_no_overwrite_policy`: `anon` and `PUBLIC` now have no table privileges; authenticated users can select/insert documents, update only `status` and `metadata`, and select/insert versions. Owner RLS policies explicitly target `authenticated`; document delete policy was removed. The Doka Storage object-update policy was also removed so the UI cannot replace existing objects. Verified effective table privileges and live Storage policy list after migration.
- Supabase Security Advisor reports only the previously acknowledged leaked-password-protection warning. Performance Advisor currently reports three unused indexes, expected before real data/query traffic exists; re-evaluate after representative query traffic.
- A free-cloud architecture decision is documented in `docs/DOKA_FREE_CLOUD_ARCHITECTURE.md`: Vercel for UI, Supabase Auth/Postgres, Supabase Storage initially, provider-neutral object storage with Cloudflare R2 as the larger-storage option, and a remote Python/OCR runtime to be selected only after Phase D workload measurements.
- Render Free is explicitly not selected as the durable Doka data plane because its filesystem is ephemeral.
- External services must remain optional and must not be required for local operation.
- Local and cloud storage should be separate adapters behind stable document/storage interfaces.
- AI provider identity/model/method/confidence should remain provider-neutral.
Do not migrate the Personal Local data plane to cloud infrastructure merely to satisfy Phase E. The enterprise edition starts after the local safety/workflow gate is proven.

## Current status
| Phase | Repository state | Final gate |
|---|---|---|
| A | Implemented + regression covered | Automated security tests — latest Local Core Checks and Doka Quality Checks pass |
| B | Implemented + regression covered | End-to-end local browser workflow on a real running instance |
| C | Implemented + regression covered | Representative Myanmar/English quality test |
| D | Pilot harness added + deterministic CI regression | Real machine + copied office dataset |
| E | Boundary documented; Vercel + Supabase Auth integration prepared; free cloud-first architecture documented; provider-neutral storage code implemented; runtime selection deferred | Architecture review after D + real workload measurements |

## Main-branch rule
All Doka work is committed directly to main as requested. No feature branch is required for this delivery sequence.

### Code completion update
- Provider-neutral cloud storage interface: implemented.
- Live Supabase schema and private bucket: provisioned with SQL migrations and verified.
- Supabase Storage adapter: implemented; uses the signed-in user's access token and private-bucket model.
- Cloudflare R2 adapter: implemented behind the same interface.
- Storage key/path validation, SHA-256 checks, object-size guard, optional total quota guard, and signed GET URLs: implemented.
- Authenticated cloud-storage API primitives: implemented.
- Storage is still disabled by default and requires manual bucket/provider configuration before real-data use.
- Cloud Documents frontend now calls the dedicated FastAPI Cloud API (`app.cloud_main:app`) and forwards the signed-in user's Supabase access token. The cloud API verifies tokens through Supabase Auth and uses that same user token for owner-scoped PostgREST and private Storage operations; no service-role key is exposed. The cloud API deliberately does not mount local workspace, filesystem import, backup, OCR, or local-password-auth routes. Added `web-platform/backend/requirements-cloud.txt`, `render.yaml` (free Singapore Web Service blueprint), and `docs/DOKA_FASTAPI_CLOUD_DEPLOYMENT.md`. The frontend uses `VITE_API_BASE_URL` for the API origin while local Vite proxy behavior remains unchanged. Render is not used for production. The Cloudflare Worker is deployed at `https://doka.logixaflow.workers.dev`; Vercel frontend and Supabase Auth are configured. Authenticated upload/download and cross-user isolation E2E remain pending.
- Remote OCR execution, real copied-office pilot, authenticated browser E2E, and downloadable thin client remain validation/integration work.
- Production bundle inspection confirms `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` are compiled into the Vite frontend using the active Supabase project configuration; the publishable key is intentionally browser-safe. `VITE_API_BASE_URL` is not compiled and must remain unset until a Python API host/proxy is configured. Requests to production `/api/documents` and `/api/config` still return the SPA `index.html`, not FastAPI JSON, so workspace/OCR API routes are not remotely available. Basic Cloud Documents operations use the browser's signed-in Supabase session directly against PostgREST and private Storage, and do not require that Python API. The `/admin/cloud-documents` path returns the SPA entry page (HTTP 200), and the production JavaScript bundle contains the Cloud Documents route/UI. Real signed-in upload/download and cross-user isolation E2E remain unverified. Never place a Supabase service-role key in the frontend.
- Frontend Sentry React SDK integration is still pending; this frontend is Vite/React, so the supplied Next.js wizard command is not applicable. See `docs/DOKA_SENTRY_AND_CLOUDFLARE_SETUP.md`.
- Cloudflare R2 remains optional and is not activated; current Cloudflare onboarding requires an R2 subscription checkout before API token creation. Do not proceed if it requires a card or paid billing under the free-only project constraint.
- Latest Vercel deployment observed on 2026-10-01 is READY for main commit `65dc596` (`fix(security): restrict Doka Data API table privileges`), and the production alias `https://enterprise-ai-dms.vercel.app` serves the Vite SPA entry page (HTTP 200). The `/admin/cloud-documents` path also returns the SPA entry page (HTTP 200); the production bundle contains the Cloud Documents UI and compiled Supabase public configuration. This verifies deployment of the UI, not successful interactive authentication or a real upload/download. `/api/*` still has no FastAPI proxy/runtime.
- The previously verified Doka Quality Checks run `36845369692` and Local Core Checks run `36845369664` passed on their recorded commits. The latest database-migration and documentation commits do not change application code; no new full test run was claimed for those commits.
- Python API hosting is still deliberately unselected; Vercel is the frontend host, not the Python OCR runtime.


## 2026-10-01 follow-up audit and hardening
- Fixed cloud upload compensation so a failed Storage PUT (including an already-existing object with Supabase `x-upsert=false`) never triggers deletion of that pre-existing object. Cleanup now runs only after this request's PUT completed successfully.
- Added focused regression tests for pre-existing object preservation, successful-request cleanup, and cleanup-error isolation.
- Hardened backend Sentry scrubbing to remove exception messages, frame locals/source paths, log messages, arbitrary tags, request payloads, and user-supplied transaction metadata while retaining safe exception type/function metadata.
- Added regression coverage for exception/stack-frame/log-entry scrubbing.
- Added `pytest-cov` to the local backend test dependencies and corrected backend pytest discovery to target the shared `web-platform/tests` directory with the backend app on the import path.
- Added `.github/workflows/doka-quality.yml` to run backend regression tests and frontend build/smoke tests on relevant main pushes and pull requests. Latest Doka Quality Checks run `36845369692` on commit `9a0cc40` completed successfully: backend `46 passed`; frontend `npm ci`, npm audit reporting, TypeScript/Vite production build, existing smoke test, Supabase cloud-document integration smoke test, and Cloud Documents route smoke test all passed. The source code under test is unchanged from code commit `59d9ebe`.
- The existing `Local Core Checks` workflow also passed on latest main commit `9a0cc40` (run `36845369664`): backend `43 passed`, Python syntax compilation passed, and frontend build + all three smoke checks passed. These are separate suites with different test scopes; do not combine their counts.
- The successful Doka Quality Checks run reported 8 npm audit findings (1 low, 1 moderate, 6 high) across eight package names: `baseline-browser-mapping`, `brace-expansion`, `browserslist`, `esbuild`, `js-yaml`, `nanoid`, `postcss`, and `react-router` (one package contributes multiple advisories). Direct dependencies flagged are `postcss` (locked at 8.5.15) and `react-router` (locked at 7.18.0); the others are transitive. npm reports a fix available for each package, but the lockfile has not yet been changed; review and apply patched lockfile versions, then rerun CI. Do not run a blind major upgrade. The latest backend test runs also report three Pydantic deprecation warnings in `config_validator.py` and GitHub Actions Node 20 deprecation warnings for older action versions.
- The latest observed READY Vercel production deployment is commit `65dc596` (`fix(security): restrict Doka Data API table privileges`). This supersedes the earlier `3e4664c` deployment reference. The previous build-rate-limit issue no longer blocks this latest application-code commit; subsequent documentation-only commits may still trigger their own Vercel build.
- Frontend Sentry SDK/source-map integration remains pending because npm is unavailable in the connected repository-editing environment and the lockfile must be regenerated by npm (never hand-edited). The React Native wizard command is not applicable to the React/Vite frontend.
- Latest Doka Quality Checks run `36847031988` on commit `93a8260` passed: backend `46 passed`; frontend `npm ci`, npm audit reporting, TypeScript/Vite production build, and all three smoke checks passed. This run includes the backend CORS environment-template update. A later `.gitignore`-only commit does not change application code. The subsequent Local Core Checks run `36847085490` on commit `19b1f8d` also passed: backend `43 passed`, Python syntax checks, frontend production build, and all three smoke checks.


## 2026-10-01 live environment and authorization verification
- Supabase project `jkobgssaqifzrqfirdfu` is `ACTIVE_HEALTHY`; the project URL and active publishable key match the values compiled into the production Vite bundle. The private `doka-documents` bucket is present with `public=false` and a 52,428,800-byte limit.
- Vercel's connected tools in this session expose project/deployment reads but no environment-variable list/create/update operation. The production bundle proves the two public Supabase Vite values were supplied at build time; it does not expose the Vercel dashboard's full environment-variable inventory. Do not claim dashboard-level env auditing or key rotation was performed.
- Required Vercel frontend variables: `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. Keep `VITE_API_BASE_URL` unset until a real Python API host and HTTPS route exist. Do not add service-role, AI-provider, R2, or backend-only secrets to Vercel's browser bundle.
- Leaked-password protection remains the sole Supabase Security Advisor warning and requires review in Supabase Auth settings. Do not change it blindly because availability may depend on project plan/settings.

- Supabase migration `20261001100500_doka_storage_no_overwrite_policy` is committed and applied; live Storage policy query now shows only Doka SELECT, INSERT, and DELETE policies for `authenticated`.


### Cloud library lifecycle implementation update — 2026-10-02
- Added recoverable Trash and Restore, filename search, status filter, pagination, rename and folder-path move to the Personal Cloud API/UI.
- Added account-scoped Activity/Audit history: `doka_audit_events` has RLS and narrow authenticated grants; the Worker records upload/download/update/trash/restore events and exposes `GET /api/audit`.
- Added `deleted_at` and `folder_path` to `doka_documents` with owner-scoped RLS retained and narrow column grants.
- The current contract is documented in `docs/DOKA_CLOUD_API_CONTRACTS.md` and `shared/contracts/cloud-document.schema.json`.
- Permanent deletion, version creation/restore, preview and bulk operations are still deferred until object cleanup and version concurrency semantics are implemented and tested.
- Latest CI/Worker/Vercel evidence is tracked in `docs/DOKA_MASTER_PRODUCT_PLAN.md`; authenticated user-flow and two-user isolation tests remain outstanding.

### Latest acceptance evidence — 2026-10-02
- Production Login accessibility inspection succeeded at 390px; measured document/body width was exactly 390px. At 1440px, document/body width was exactly 1440px. No horizontal overflow was detected on Login at those two widths.
- This does not certify the authenticated dashboard/sidebar; a real signed-in session is still required to inspect those pages and complete cloud E2E.
- Doka Quality Checks run 36982859866 passed with 48 backend tests plus TypeScript/Vite build and frontend smoke tests.
- Local Core Checks passed on 36c14a39 and the documentation-only follow-up f459c11.
- Vercel production deployment dpl_AGL7K8ejPDYx1rj9bZ6fWAHMMRhB is READY. Cloudflare Worker build 9ab06efb-f44a-41e6-bc85-9345937d46a7 completed successfully.
- Remaining blockers: eight npm audit findings, Supabase leaked-password protection warning, authenticated cloud E2E/two-user isolation, real-office OCR pilot, and not-yet-implemented enterprise APIs.


### Current cloud delivery update — 2026-10-02 (latest pass)

- Cloud API now includes owner-scoped permanent deletion for trashed documents only. The Worker deletes the current Storage object and any registered version objects before deleting metadata; Storage cleanup failure retains metadata.
- Supabase DELETE privilege is protected by an RLS predicate requiring both `auth.uid() = owner_id` and `deleted_at IS NOT NULL`. The migration history now records `doka_permanent_delete` and `doka_audit_events`; migration files use matching applied versions and are replay-order safe.
- Audit actions now include `permanent_delete`; the original document UUID is retained in audit metadata after document metadata is removed.
- Cloud Documents UI now supports confirmed permanent removal from Trash, bulk status changes and bulk move-to-Trash. Bulk operations currently issue individual authenticated requests and are not atomic.
- CI passed on the cloud UI code commit `c02599bc` (Doka Quality Checks and Local Core Checks). The later migration/documentation commits are being checked by Local Core Checks.
- Vercel production deployment for UI commit `c02599bc` reached READY. Cloudflare Worker build for backend commit `e9125d30` completed successfully and a new Worker version received 100% traffic.
- Supabase Security Advisor still reports leaked-password protection disabled. Performance Advisor reports five unused indexes; retain them while the tables are small and re-evaluate with representative workload before removing indexes.
- Still open: version creation/list/restore, safe preview, folder tree, batch upload queue/retry, authenticated lifecycle browser test, two-user isolation test, local OCR pilot, production team APIs and production AI workflow.


### Safe preview delivery — 2026-10-02

- Added `GET /api/documents/{id}/preview` with verified owner/non-trash checks and a 5-minute signed URL.
- Preview allowlist is restricted to PDF, JPEG, PNG, GIF, WebP, plain text and CSV. HTML, SVG and other active/unknown formats return HTTP 415.
- Preview actions are written to the owner-scoped audit log.
- Added migration `20261002091601_doka_audit_preview` and a Worker contract regression test.
- Preview controls are shown only for supported MIME types in Cloud Documents.
- The UI preview commit and Worker preview endpoint are in the deployment pipeline; final CI and deployment checks are required before claiming the feature is live.


### Cloud version history — 2026-10-02

- Added owner-scoped GET/list, multipart replacement upload and restore routes for cloud document versions.
- Version creation and restore use database functions that validate the signed-in owner and atomically preserve the previous active object metadata.
- Version rows are protected by RLS through their parent document; the version migration is replayable from a clean Supabase project and extends the existing schema safely.
- Added UI history dialog, version upload, SHA-256/date/size display and confirmed restore.
- Added audit actions for version creation and restore.
- Remaining Phase 1 tasks are atomic bulk APIs, richer folder-tree management and batch upload progress/retry.


### Deployment verification — 2026-10-02 09:33 UTC

- Cloudflare Worker build for repository commit `1c9a8287` completed successfully and a new Worker deployment version is receiving 100% traffic. This includes the version history/create/restore API.
- Vercel production currently resolves to deployment commit `77be1bd0` (READY). The production JavaScript bundle contains bulk actions and safe preview, but does not yet contain the newly added Version history UI.
- Latest frontend source is committed and CI is passing; Vercel has not created a deployment for the subsequent frontend commits yet. Do not describe version controls as live in the production browser until the Vercel deployment is updated and the production bundle is rechecked.
- Authenticated end-to-end tests and two-user isolation remain open because no real signed-in test session is available in this run.


### Atomic bulk operations — 2026-10-02

- Added `POST /api/documents/bulk` for up to 100 unique documents.
- Bulk status updates and Trash execute through a single SECURITY INVOKER Postgres function under existing authenticated grants and RLS; all IDs are validated before any update, so partial batches are rejected.
- Audit events are inserted in the same transaction.
- Frontend bulk controls now call the single atomic endpoint rather than issuing parallel per-document requests.
- Added null-action validation, migration and regression/smoke coverage.

### Current cloud acceptance snapshot — 2026-10-02 09:45 UTC

- Cloud library now has owner-scoped folder-path filtering and a folder-list endpoint. Folder paths remain logical metadata; they do not rewrite immutable Storage object keys or SHA-256 identity.
- Batch upload queue is available in the UI: sequential uploads, per-file queued/uploading/complete/failed states, 50 MiB per-file validation, and retry of failed items.
- Version history (list/create/restore), safe preview, permanent deletion, audit history, and atomic bulk status/Trash operations are implemented in the Worker and UI. Bulk requests validate 1–100 unique document IDs and execute through one SECURITY INVOKER Postgres function; audit inserts occur in the same transaction.
- Live Supabase migration history currently contains 21 applied Doka migrations through `20261002100658_doka_version_object_key_pattern`, including document lifecycle, folder validation, permanent delete, audit, versions, version RPCs, atomic bulk actions and the timestamp-trigger privilege correction.
- Local Core Checks run `36991467934` completed successfully on main commit `a723b4cb6b4cc0ba5ee34e62054c7e50a8b61e25`: backend tests, frontend build/tests, and Python syntax compilation all passed.
- Vercel production deployment `dpl_94Z3TeFYrkfxTZo7XBhziJ2FGSoQ` is READY for UI commit `1b6ac3a5d85e9f2c7a8fad313c6add879364388c`; the production alias is `https://enterprise-ai-dms.vercel.app`.
- Cloudflare Worker deployment now routes 100% traffic to version `3deafab7-ec4f-4fe7-adbf-fcd883732fdd` (version number 121), created at 10:21:49 UTC. It includes folder listing, version history, audit, atomic bulk APIs, safe reuse of previous version objects and filename/MIME validation. Worker bindings show the Supabase publishable key as a secret binding; no service-role key is configured in the Worker.
- Remaining acceptance gates: authenticated real-user upload/download/preview/version/trash/restore flows, two-user isolation, representative Myanmar/English OCR pilot, leaked-password protection review, and a verified review/remediation of the Dependabot/npm advisory set. A private-repository Dependabot alert listing was not available through the connected GitHub read endpoint in this check; no alert is claimed fixed.

- Deployment automation note: the Vercel GitHub Actions workflow's invalid job-level `secrets` condition was corrected to a step-level token check. The corrected run `36991704683` passed, but its deploy/build steps were intentionally skipped because the `VERCEL_TOKEN` GitHub secret is not configured. Vercel's connected Git integration subsequently produced deployment `dpl_BoY7ur6K8751F77DsGPoRsPvtutS` for commit `7846669f`; do not interpret the workflow's successful token-check run as a deployment.


### Folder filters, atomic bulk and batch queue — 2026-10-02

- Added `GET /api/folders` for distinct active folder paths scoped to the authenticated owner and a matching folder filter in Cloud Documents.
- Bulk status and Trash now call one atomic database RPC for up to 100 unique IDs. It validates every document before updating and writes audit events in the same transaction; no partial batch is applied.
- Added sequential multi-file upload queue with 50 MiB per-file checks, per-file queued/uploading/complete/failed states and retry of failed items. Byte-level progress and resumable chunk upload remain open.
- Added Vercel production deploy workflow using a pinned CLI and the existing project/team IDs. The workflow ran successfully but skipped deployment because the GitHub Actions `VERCEL_TOKEN` secret is not configured; production still needs that secret before new frontend code can be published automatically.
- Cloudflare Worker version 87 is receiving 100% traffic, so the folder-listing, atomic bulk and version API changes are deployed. Real authenticated browser acceptance remains open.


### Latest runtime rollout — 2026-10-02 10:00 UTC

- Cloudflare Worker version `3deafab7-ec4f-4fe7-adbf-fcd883732fdd` (version number 121) is receiving 100% traffic as of 10:22:01 UTC. Its bindings include the Supabase publishable key as a secret and no service-role key. It contains the SHA-bound safe object-key and version metadata validation.
- Supabase schema/function checks confirm the version table, owner-scoped RLS policies and RPC permissions. `anon` cannot execute the version or bulk RPCs; authenticated users can execute only the intended functions. Bulk updates rely on column-level grants and RLS.
- GitHub Actions `Doka Quality Checks` passed on commit `5ad3efa7`, including backend regression tests and frontend build/smoke tests. Local Core Checks passed on commit `0807b5c3`.
- Vercel production deployment `dpl_AQKs3XXaQnjipmWqq4sRPyjyDmhX` (commit `ee1def5b`) is READY. This commit is downstream of the npm lockfile remediation commit `82273315`, so the production build uses the patched dependency lockfile. Its production bundle includes Version history, safe preview, folder filtering, atomic bulk actions, Activity and the batch upload queue/retry. The GitHub Actions CLI fallback still skips without `VERCEL_TOKEN`; the connected Vercel deployment is verified independently.
- Supabase Security Advisor still reports the intentional authenticated `SECURITY DEFINER` version RPCs and disabled leaked-password protection. The version RPCs explicitly validate `auth.uid()`, owner and user-scoped object paths; the warning is retained for review. The bulk RPC is SECURITY INVOKER.


### Phase 2 OCR benchmark foundation — 2026-10-02

- Added `web-platform/backend/app/services/ocr_benchmark.py` and `scripts/ocr_benchmark.py` to calculate CER/WER on copied Myanmar/English PDF/image samples.
- Sample paths must be relative and symlink-free; traversal is rejected. Reports must be written outside the sample root.
- Reports contain sample IDs, metrics and aggregate language scores only; recognized and reference text are excluded.
- Added regression tests for Unicode normalization, Levenshtein scoring, path safety and report privacy.
- Phase 2 remains open until representative local sample data is supplied, OCR is run on the target machine, and manual accuracy thresholds are accepted.

### Version RPC security hardening — 2026-10-02 09:56 UTC

- Applied and committed migration `20261002095530_doka_harden_version_rpc_guards` (18 Doka migrations applied in live Supabase).
- Version replacement and restore RPCs now reject unauthenticated/null input, validate document ownership, validate both current and selected object keys against the caller's `users/{auth.uid()}/documents/` prefix, validate metadata, and pin `search_path` to `pg_catalog, public, pg_temp`.
- Function ACLs were rechecked: `anon` cannot execute either RPC; `authenticated` can execute the two intended Worker RPCs. Authenticated users still have no direct UPDATE grant on document object-key/hash/size/content-type columns.
- A live SQL regression check confirmed both RPCs reject unauthenticated null calls with insufficient privilege. Static regression coverage was added to the Worker/database contract test suite.
- Security Advisor continues to report the two authenticated SECURITY DEFINER RPCs because those narrowly scoped functions must update protected storage-pointer columns atomically without widening direct table privileges. The code now documents the rationale and has explicit owner/path/input checks; the warning is not represented as cleared.
- Leaked-password protection remains disabled. Current Supabase documentation states this feature is available on Pro and above; no plan change or paid upgrade was made. It requires review in Supabase Auth settings if the project plan supports it.
- Doka Quality Checks now run the Worker/database contract tests and upload the npm audit + ESLint JSON reports as a short-lived artifact so dependency advisories can be reviewed from the actual CI result.

### Dependency remediation and final RPC validation — 2026-10-02 10:05 UTC

- Frontend npm audit baseline contained 8 vulnerable package records (6 high, 1 moderate, 1 low). SemVer-compatible `npm audit fix --package-lock-only` upgraded the lockfile without changing direct dependency declarations.
- Verified lockfile versions include PostCSS 8.5.28, React Router 7.18.4, Browserslist 4.29.3, js-yaml 4.3.2, nanoid 3.3.19, brace-expansion 1.1.21, baseline-browser-mapping 2.11.27 and esbuild 0.27.2.
- Post-remediation `npm audit --audit-level=low` reports **0 vulnerabilities**. The remediated `package-lock.json` was committed as `82273315` (`fix(deps): remediate frontend npm advisories`).
- Doka Quality Checks run `36993280544` passed backend tests, Worker/database contract tests, frontend build, frontend smoke tests and the zero-vulnerability npm audit. The verified dependency lockfile was committed by the CI remediation step.
- Live Supabase migration history now contains 21 Doka migrations through `20261002100658_doka_version_object_key_pattern`. The final migration binds object keys to the caller, SHA-256 and one safe path segment, and retains filename/MIME validation plus a fixed search path.
- Regression tests now target the final SHA-bound single-segment object-key migration. A separate live SQL check verified unauthenticated RPC calls are rejected. No live document rows currently exist, so a valid authenticated version create/restore cycle and cross-user isolation still require real-user acceptance testing.
- Security Advisor still shows two intentional authenticated SECURITY DEFINER RPC warnings and the leaked-password-protection warning. The two RPCs remain narrow, owner-checked and unavailable to `anon`; leaked-password protection is a project Auth setting and current Supabase documentation limits it to Pro and above. No paid plan change was made.
- The connected GitHub integration did not expose the private repository's Dependabot alert listing. The npm audit findings above are fixed, but the separate Dependabot alert count is not claimed as cleared.
- ESLint baseline remains 172 errors and 5 warnings across 51 files (primarily unused variables and React/TypeScript rule findings); this is tracked as separate code-quality debt and was not hidden by the dependency remediation.

### Latest security and rollout verification — 2026-10-02 10:14 UTC

- Final live Supabase version RPC inspection confirms both functions use the pinned `pg_catalog, public, pg_temp` search path, reject missing auth, enforce the safe SHA-bound single-segment key pattern, deny `anon` execution and allow only the intended authenticated Worker calls.
- Live SQL regex probes accepted a valid user-owned object key and rejected nested paths, traversal, another user's prefix and SHA mismatch.
- Latest Doka Quality Checks run `36994164252` passed backend regression tests, Worker/database contract tests, frontend build, frontend smoke tests and `npm audit --audit-level=low`. The npm audit gate reports zero vulnerabilities after the lockfile fix.
- Current Vercel production deployment `dpl_AQKs3XXaQnjipmWqq4sRPyjyDmhX` is READY at commit `ee1def5b`, which includes the patched npm lockfile. Current Cloudflare Worker version `3deafab7-ec4f-4fe7-adbf-fcd883732fdd` (version 113) receives 100% traffic.
- Supabase organization plan is Free. Current Supabase documentation makes leaked-password protection a Pro+ feature, so it cannot be enabled on the current plan without a paid upgrade; no upgrade was made.
- Security Advisor still reports the two intentionally narrow owner-checked SECURITY DEFINER version RPCs and leaked-password protection. Performance Advisor reports five unused indexes as INFO; these are retained pending real document/audit workload rather than removed prematurely.
- Live Doka document tables currently contain zero active document rows. Authenticated lifecycle and two-user isolation therefore remain unverified against real user data and are still explicit acceptance gates.

- Post-remediation production browser-surface check: `https://enterprise-ai-dms.vercel.app` returned HTTP 200. The current production JavaScript bundle contains Version History, Preview, folder filtering, batch upload retry and Activity UI.
- Latest Doka Quality Checks run `36994469212` completed successfully after the CI lockfile-push retry/rebase improvement; backend regression, Worker/database contract tests, frontend build/smoke tests and the low-severity npm audit gate all passed.

### Backend validation cleanup — 2026-10-02 10:18 UTC

- Migrated config_validator.py from deprecated Pydantic v1 @validator/min_items APIs to Pydantic v2 @field_validator, ValidationInfo and min_length; default serialization now uses model_dump().
- Added regression tests for valid/invalid threshold ordering and non-empty keyword lists.
- Latest backend CI run passed 64 regression tests plus 10 Worker/database contract tests, with the prior Pydantic deprecation warnings absent.

- Repository root cleanup: archived the inactive Render deployment manifest at archive/deployment-configs/render.yaml and removed render.yaml from the root. The active deployment configs remain vercel.json and wrangler.jsonc, matching the current Vercel + Cloudflare Worker architecture.


### Follow-up verification — 2026-10-02 11:42 UTC

- Removed the misleading CLI deployment fallback behavior from the Vercel GitHub Actions workflow. The previous workflow reported success while skipping pull/build/deploy because the `VERCEL_TOKEN` secret was absent.
- Vercel Git Integration independently created production deployment `dpl_DSqnzHbC4vb3z9to8jbsjWnMsP2M` for main commit `3cd0f966` with state READY. The deployment URL returned HTTP 200 and the expected Doka page title.
- Replaced the secret-dependent workflow with a production smoke check that waits for the Git Integration deployment and verifies the public production alias responds with HTTP 200 and the expected document title. This workflow verifies a deployment; it does not claim to create one.
- Latest `Doka Quality Checks` and `Local Core Checks` both passed on commit `3cd0f966`, including backend regression, Worker/database contract tests, frontend build, smoke tests, and Python syntax checks.
- Latest npm audit artifact reports zero vulnerabilities at all severities.
- ESLint baseline remains 141 errors and 5 warnings across 49 files. The largest categories are unused variables (79), React Refresh export-boundary findings (25), explicit any (18), and React Hooks rule findings. This debt remains open; it is not waived or described as clean.
- Dependabot's private alert list remains unavailable through the connected GitHub integration. The zero-vulnerability npm audit is verified separately and does not prove every Dependabot alert has been dismissed.
- Real signed-in cloud lifecycle tests, two-user isolation, and representative Myanmar/English OCR pilot still require valid user sessions and representative copied data; they remain acceptance gates.


## 2026-10-02 follow-up audit — repository cleanup and cloud ACL review

- Removed the duplicated CloudDocumentVersion API block that caused the TypeScript build failure.
- Updated the Vercel workflow to describe and perform a production-alias smoke check; Vercel Git Integration remains the deployment owner. A successful smoke check proves the alias serves the expected SPA, not that a particular Git SHA was deployed.
- Removed unused imports in 16 frontend files across the follow-up cleanup commits. On commit `462518cc271b152f13170f14bb8ef4cc5b5a77cf`, Doka Quality Checks and Local Core Checks passed; frontend TypeScript/Vite build and smoke tests passed.
- Latest quality artifact for that commit: npm audit reports 0 vulnerabilities; ESLint reports 97 errors and 5 warnings across 125 scanned files. This is down from the earlier 141 errors and 5 warnings; remaining errors include 35 unused-variable findings, 25 React Refresh export findings, 18 explicit-any findings, and hook/purity findings. Do not suppress rules wholesale; fix behavior-sensitive hook findings individually.
- Latest verified production Vercel deployment observed is READY for commit `3183641d4ae9a807784d9c61696e90fe40ca1de1`. The smoke check on later cleanup commits passed against the production alias, but a deployment for the later frontend-cleanup SHA was not present in the deployment list at the time of this audit. Treat exact-SHA deployment verification as pending.
- Live Supabase security review found broad default ACLs on `public.doka_audit_events`: `anon` and `authenticated` had broad table privileges even though RLS had owner-scoped select/insert policies. Applied migration `20261002114801_doka_audit_least_privilege` and committed the matching migration file. Verified effective ACL: anon has no SELECT/INSERT; authenticated has SELECT/INSERT only and no UPDATE/DELETE. Owner-scoped RLS policies remain enabled.
- The two version RPCs remain intentional `SECURITY DEFINER` functions because they atomically update immutable storage-pointer columns that authenticated clients cannot update directly. Verified fixed `search_path=pg_catalog, public, pg_temp`, explicit `auth.uid()` owner checks, anon EXECUTE denied, and authenticated EXECUTE granted. Supabase Advisor continues to flag these two functions because they are exposed to authenticated callers; keep this documented exception unless the architecture is redesigned without granting direct object-pointer updates.
- Supabase Auth leaked-password protection remains disabled and needs an Auth dashboard setting change; no connected settings operation is available in this session. Performance Advisor currently reports five unused indexes; defer index removal until representative query traffic is available.
- Dependabot alert details remain inaccessible through the connected GitHub API in this session. The npm audit result is clean but is not evidence that all Dependabot alerts are resolved.
- Remaining release gates: exact-SHA production deployment confirmation; frontend lint remediation; Dependabot alert review; signed-in cloud upload/download/version/trash/restore/permanent-delete tests and two-user isolation; real-machine Myanmar/English OCR pilot; and documented Phase D source-unchanged + backup/restore acceptance.

- A second live ACL pass found that the original version-history migration had granted authenticated DELETE on `doka_document_versions` and added an owner-delete policy. No supported user-facing route requires deleting an individual version; permanent document deletion removes versions by FK cascade. Applied and committed `20261002115107_doka_version_history_append_only`, revoking direct authenticated version deletion and dropping the delete policy. Rechecked all three Doka tables: anon has no SELECT/INSERT; authenticated audit/version tables have SELECT/INSERT only; documents retain DELETE only for the trashed-document permanent-delete flow, with the owner + trashed RLS predicate.

- Cloudflare Worker audit found duplicate GET/POST version route registrations in `cloudflare_worker/main.py`; the earlier handlers were registered first and could shadow the later, stricter handlers. Removed the earlier duplicate block. Added regression tests asserting unique method/path route pairs and checking the new audit/version ACL migrations. The corrected test suite passed on commit `a800a7250b91b47e707cb982f642d759fae3980c`.
- The source fix is committed but is not yet confirmed live on Cloudflare. The deployed bundle contains binary WASM modules; a direct multipart re-upload through the API re-encoded binary content and failed Worker validation. Traffic was explicitly rolled back to last known-good Worker version `42330295-944d-465e-8679-7d7523f28720` (100%). Do not claim the duplicate-route fix is in production until a proper Wrangler build/deploy from the repository is completed and the live Worker is smoke-tested. The Worker source upload endpoint now contains a newer un-deployed candidate; the active traffic remains on the rollback version.

- Additional safe frontend cleanup removed the remaining reported unused declarations, unused imports, unused catch bindings, and dead local helpers in the touched files without changing feature behavior. Doka Quality Checks and Local Core Checks passed on commit `f95a628c010ffeacf4635ed4b6214832ac8ce6ef`.
- Latest frontend quality artifact on that commit: npm audit has 0 vulnerabilities; ESLint is down to 62 errors and 5 warnings across 34 files with findings, and `@typescript-eslint/no-unused-vars` is now 0. Remaining findings are concentrated in React Refresh export boundaries (25), explicit `any` types (18), and React hook/purity rules (22 combined), plus two isolated rules. Do not silence these globally; address them by file with regression tests.
- Vercel deployment inventory was rechecked after the frontend cleanup. The latest deployment still points to commit `ff02086ecb4709507578d799ecb8ad28bdaec3fb`; later frontend cleanup commit `f95a628...` does not yet appear as a Vercel deployment. The production-alias smoke check passes, but it only verifies the currently served Doka SPA and is not proof that the latest SHA is deployed. Exact-SHA deployment remains an open release gate.

### 2026-10-02 latest security, quality and production verification

- Main is at `ff03a3e7df2fd7cd53af7696d8eb4eee96a3fc76`. Latest Doka Quality Checks run `37010356158` and Local Core Checks run `37010357177` both passed on this commit. Backend regression tests, Worker/database contract tests, Python syntax checks, frontend production build and frontend smoke tests passed.
- Backend dependency audit initially found 20 PyJWT advisory records against the old `2.10.1` pin in the production and full dependency profiles. Upgraded all five backend dependency profiles to patched `PyJWT 2.15.1`, added a hard-fail backend audit gate, and re-ran both audit profiles: zero unignored vulnerability findings. Added a 32-byte minimum HS256 signing-secret requirement and corrected the Local Core CI fixture to use a valid test secret; Local Core Checks now pass.
- Latest frontend audit reports zero npm vulnerabilities. ESLint report on this commit contains **0 errors and 0 warnings**; non-component exports used by hooks, utility generators and shadcn helpers are explicitly allowlisted in the React Refresh rule rather than disabling the rule globally.
- Vercel production deployment `dpl_3Pm4nuAG2sfPGtthV2v8KvN81Qk4` is READY for commit `607a17525ef9200adabc07f4dba185c68392782a`. This commit contains the latest application/runtime changes; the three commits after it only adjust CI workflows and ESLint configuration. The production alias `https://enterprise-ai-dms.vercel.app` returned HTTP 200 with the expected Doka title. Vercel Production Smoke Check passed on latest main. A 24-hour production error-level runtime-log query returned no entries.
- The connected GitHub integration still cannot read the private Dependabot alert listing. Clean npm and pip-audit reports are verified independently; do not infer that every Dependabot alert has been dismissed from those reports. No open pull requests were listed during this check.
- Remaining acceptance gates are unchanged: deploy the corrected Cloudflare Worker source through a proper Wrangler build and verify live traffic; run authenticated upload/download/preview/version/trash/restore/permanent-delete and two-user isolation tests with real user sessions; complete representative Myanmar/English OCR benchmarking and the copied-real-data Phase D pilot with source-hash and backup/restore evidence; review the documented Supabase Auth leaked-password setting and intentional SECURITY DEFINER advisor warnings.

### 2026-10-02 live platform follow-up — supersedes earlier snapshots above

- Main is at `34da46e0773b44e47476e3e3d0de45e339d06e15` at this verification point. Earlier dated notes in this file are historical snapshots; use this section for the latest verified state.
- The latest complete passing CI pair is Doka Quality Checks run `37010356158` and Local Core Checks run `37010357177` on commit `027885635c09c6d4a8bd40978f9b06ad0f549f2f`. Frontend production build/smoke, backend regression, Worker/database contract tests, Python syntax, dependency audit and Local Core checks passed. The latest ESLint report is 0 errors / 0 warnings; frontend npm audit is 0 vulnerabilities; backend pip-audit reports zero unignored findings after all five dependency profiles were raised to PyJWT 2.15.1. On current docs-only main commit `34da46e`, Local Core run `37011897349` (including retry attempt 2) failed before runner assignment: all jobs show runner_id 0 and no steps. Treat this as GitHub-hosted runner provisioning/billing availability, not as a code-test failure; re-run once GitHub assigns runners.
- Subsequent main commits after that passing CI pair change CI configuration, documentation and the guarded Cloudflare deploy workflow, not frontend runtime code. The latest Vercel production deployment `dpl_3NK4bsgPdtv1mmc5psyyrTtunDfz` is READY for the exact current main SHA `34da46e0773b44e47476e3e3d0de45e339d06e15`. The production alias returned HTTP 200 with the expected Doka title. This confirms the current main revision is deployed to Vercel.
- Cloudflare production API now reports active deployment `e9bf9ad3-2083-49e9-8cdf-bf892c61a950`, with Worker version `d5792574-86d0-4ac1-b1fe-e2252cd200ea` (version 179) receiving 100% traffic. The production multipart script was inspected; its `main.py` matches the repository source after whitespace normalization, including all 16 routes, and includes `/health`. The pinned Pywrangler deployment workflow was added, but run `37010810377` and its retry failed before a GitHub runner was assigned (runner_id 0, no steps). The external health URL was not reachable from the verification environment. Therefore live version/source parity is verified, but the workflow's build/deploy execution and live HTTP health probe still need a successful rerun.
- Live Supabase verification: project is ACTIVE_HEALTHY on PostgreSQL 17.6.1. All three Doka public tables have RLS enabled. No anon table grants were found; authenticated document updates are column-limited; authenticated users cannot update version rows or delete audit rows. Version history and audit tables are append-only for authenticated users. The `doka-documents` bucket is private with a 50 MiB object limit; storage policies scope access to `users/<auth.uid()>/...` within that bucket.
- A transactional RLS/RPC probe passed and was rolled back: owner-scoped document insert/update, version replace/restore, bulk status update, cross-user invisibility for documents/versions/audit, and restricted update/delete privileges were all asserted. Post-rollback counts remain zero for documents, versions, audit events and storage objects. This is a database-policy probe using one existing account plus a synthetic second UUID, not a substitute for two real authenticated sessions or file lifecycle acceptance testing.
- Supabase Security Advisor still reports two intentional SECURITY DEFINER RPCs (`doka_replace_document_version`, `doka_restore_document_version`). Both have a fixed `pg_catalog, public, pg_temp` search path, explicit `auth.uid()` checks, owner-scoped document lookups and object-key validation; EXECUTE is granted to authenticated/service_role, not PUBLIC/anon. Keep the warning documented unless the RPC architecture is redesigned. The advisor also reports leaked-password protection disabled; the organization is on the Free plan and Supabase documents this feature as Pro+ only, so enabling it requires an owner-approved plan change. Five unused-index INFO findings are expected while all Doka tables are empty; do not drop those owner/query indexes just to clear the notice.
- OCR benchmark tooling and privacy tests exist, but current tests use a mocked OCR callback. No representative copied Myanmar/English sample set or ground-truth manifest is present, so no real OCR CER/WER result is claimed.
- The private Dependabot alert list remains unavailable through the connected GitHub integration. Zero npm/pip audit findings are verified, but this does not prove every Dependabot alert is dismissed.
- Remaining acceptance gates: real authenticated upload/download/preview/version/trash/restore/permanent-delete tests; two real test accounts proving cross-user file isolation; representative Myanmar and English OCR benchmarking with an owner-approved threshold; Phase D copied-real-data pilot with hashes and backup/restore evidence; rerun Cloudflare deploy plus live HTTP health probe when GitHub runner allocation is available; confirm Dependabot alert state; and decide whether to upgrade the Supabase plan for leaked-password protection.

- The connected GitHub App cannot read branch protection (403, administration permission unavailable) or the private Dependabot alert endpoint (not an allowed endpoint). Branch protection and the actual open-alert count remain unverified; do not infer either from clean package audits.

### 2026-10-02 CI and deployment follow-up — latest

- Main is now `8afdd5e20e5e6847f4a99e4c00fc089abe958093`. The additional commits since `34da46e` modify CI workflow definitions and this status document only; no application runtime source was changed.
- CI was hardened: Local Core now runs only for relevant application, test, script, Worker, migration and workflow changes (so docs-only updates do not consume runners); it compiles both pilot/OCR CLI scripts and explicitly includes `test_ocr_benchmark.py`. Doka Quality's push and pull-request path filters now include the pilot scripts and the core/Worker deployment workflow definitions.
- Backend dependency audit was expanded from two manifests to all six maintained backend profiles: `requirements.txt`, `requirements-production.txt`, `requirements-local.txt`, `requirements-dev.txt`, `requirements-test.txt`, and `requirements-cloud.txt`. The gate now distinguishes operational pip-audit failures from vulnerability findings and expects six reports. This revised gate has not executed yet because GitHub assigned no hosted runners.
- Latest Local Core run `37014267529` and latest Doka Quality run `37014554762` ended with every job showing `runner_id=0`, blank runner name and no steps. These are pre-runner provisioning failures, not evidence of test pass or test failure. The last fully executed green CI pair remains `37010356158` (Doka Quality) and `37010357177` (Local Core) on `027885635c09c6d4a8bd40978f9b06ad0f549f2f`. Re-run both suites when GitHub runner allocation is available.
- Current Vercel production alias was re-fetched at 2026-10-02 13:39 UTC and returned HTTP 200 with title `Doka — Secure Document Workspace`. Latest READY deployment known to the integration is `dpl_3NK4bsgPdtv1mmc5psyyrTtunDfz` on `34da46e`; all main commits after it are CI/docs-only.
- Cloudflare active deployment is `2a58a5c8-f7b2-4ff7-a1a2-b731d412cf10`, Worker version `428a9941-ca87-4bbb-b232-825b1693f3cc` (version 181), receiving 100% traffic. Its deployed `main.py` was re-read and compared against repository `cloudflare_worker/main.py` from `34da46e`: all 16 routes match; only two formatting/line-wrapping differences remain. The Worker API confirms the active version and bindings. The public `/health` URL remains inaccessible to the available HTTP verification clients, so do not claim a successful live health response.
- No connected action can read private Dependabot alerts or repository secrets/administrative runner settings. The private alert count, required Cloudflare GitHub secrets and root cause of runner provisioning therefore remain owner/admin verification items.
- After the above entry, retried the latest Doka Quality run `37014554762` and Local Core run `37014267529` (attempt 2). Both again failed before runner allocation: every job still reports `runner_id=0`, blank runner name and no steps. This confirms the CI blockage persists independently of the workflow edits. No test step ran in these attempts.

### 2026-10-02 live verification follow-up — latest

- Main at verification time: `b0485f500f07bb5f65a7730a49819408b9391f53`. Vercel production deployment `dpl_2UjNcYAPRZQv44qGVtAzvCt7C3H3` is `READY` for this exact SHA and owns the production aliases. A fresh fetch of `https://enterprise-ai-dms.vercel.app` returned HTTP 200 with the expected Doka title.
- Vercel grouped runtime error query for the preceding 24 hours returned no runtime error clusters. A detailed 24-hour log query timed out before retrieval; therefore this is not evidence that all logs are empty.
- Cloudflare Worker `doka` latest deployment is `39bb5a9b-c19c-410f-9e6f-1bc4f655f1cc`, routing 100% traffic to version 185 (`2dc2093d-3ac5-48f1-a5a6-10c023c669fa`). Cloudflare API reports the version active and its runtime compatibility date/flag as expected. The deployed `main.py` was extracted from the live Worker script package and compared with repository `cloudflare_worker/main.py` on main; normalized source matched exactly (30,925 characters). The configured Supabase publishable key binding is present as a secret binding; its value was not exposed or read.
- Cloudflare Workers Observability issue summary for service `doka` reports 0 active issues, 0 active occurrences and 0 resolved issues at this check. The public `/health` URL remains inaccessible to the available HTTP verification client, so a live HTTP health response is still not confirmed.
- Latest Doka Quality run `37014554762` (attempt 2) and Local Core run `37014267529` (attempt 2) remain pre-runner failures: every job has `runner_id=0`, blank runner name and no steps. No checks ran in these attempts; the revised six-profile dependency audit and OCR benchmark workflow coverage are not yet executed.
- The Vercel and Worker deployments are current and the latest source is deployed, but this does not clear the outstanding gates: GitHub-hosted runner allocation; private Dependabot alert review; real authenticated two-user upload/download/version/trash/restore/delete acceptance; representative Myanmar/English OCR ground-truth benchmarking; Phase D copied-data hash and backup/restore evidence; and the owner decision on Supabase Pro leaked-password protection. Do not mark Phase A–E complete until these are evidenced.

- GitHub Status was checked during this follow-up: the public status page reports all systems operational, and the October 1 Actions hosted-runner delay incident is marked resolved. The repository's current `runner_id=0` failures therefore cannot be attributed to a currently declared GitHub-wide Actions incident; the exact repository/account runner provisioning or billing cause remains unverified and requires owner/admin access. Source: https://www.githubstatus.com/

### 2026-10-02 — CI quota workaround and fresh Supabase review

- Owner confirmed GitHub Actions monthly CI minutes are exhausted and reset on the 1st of next month. No additional paid runner/sandbox was provisioned. Avoid manually dispatching/rerunning Actions until the quota resets.
- The current frontend has a successful Vercel Production deployment for the latest checked main commit (`3f8a8df7bb632277c6391f6f771fb8b44553674a`), and the production alias responds HTTP 200 with the expected Doka title. This validates the deployed frontend build path, but does not substitute for backend tests, six-profile pip-audit, or full CI.
- Fresh Supabase project review (`jkobgssaqifzrqfirdfu`): project status `ACTIVE_HEALTHY`; latest applied migration `20261002115107_doka_version_history_append_only` matches the latest migration filename in the repository; all three Doka public tables have RLS enabled; no public views; private `doka-documents` bucket remains capped at 50 MiB; storage policies restrict authenticated objects to each user's `users/<auth.uid()>/...` prefix. Public table grants observed for the three Doka tables were limited to authenticated role, with service_role/postgres administrative grants.
- Fresh Security Advisor still reports two intentional authenticated-callable SECURITY DEFINER RPCs (`doka_replace_document_version`, `doka_restore_document_version`) and leaked-password protection disabled. Function ACLs show EXECUTE to authenticated and service_role; both function bodies explicitly require non-null `auth.uid()`, constrain document ownership, validate object keys/metadata, and use fixed `search_path = pg_catalog, public, pg_temp`. Keep these as documented intentional RPCs; do not blindly remove authenticated EXECUTE or convert to SECURITY INVOKER because they perform atomic multi-table version operations.
- Fresh Performance Advisor reports one INFO-only unused index (`doka_audit_events_owner_created_idx`). Do not drop it while the database is effectively empty (all three Doka tables currently report zero rows); revisit after real usage.
- Supabase has no Edge Functions deployed for this project at this check. A 24-hour unified log source summary returned rows for pgbouncer, PostgREST, Postgres, edge, Auth, audit, Realtime and Storage. A follow-up detailed log query hit a backend error, so no error-rate conclusion is recorded.
- CI-free execution constraints: the connected shell cannot resolve github.com, and the available Expo EAS sandbox is billable; neither was used. Continue static review, Supabase read-only checks, Cloudflare API/source checks and Vercel production checks without incurring new CI or sandbox charges. Do not label tests passed unless a real runner executes them.
- Remaining acceptance blockers: real authenticated two-user lifecycle/isolation tests; anonymized Myanmar/English OCR samples with ground truth; full backend test and six-profile dependency audit after CI quota resets; private Dependabot alert review; Phase D copied-data hash and backup/restore evidence; and owner decision on Supabase Pro leaked-password protection.
