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
- Live Supabase migration history currently contains 17 applied Doka migrations through `20261002095029_doka_bulk_updated_at_trigger`, including document lifecycle, folder validation, permanent delete, audit, versions, version RPCs, atomic bulk actions and the timestamp-trigger privilege correction.
- Local Core Checks run `36991467934` completed successfully on main commit `a723b4cb6b4cc0ba5ee34e62054c7e50a8b61e25`: backend tests, frontend build/tests, and Python syntax compilation all passed.
- Vercel production deployment `dpl_94Z3TeFYrkfxTZo7XBhziJ2FGSoQ` is READY for UI commit `1b6ac3a5d85e9f2c7a8fad313c6add879364388c`; the production alias is `https://enterprise-ai-dms.vercel.app`.
- Cloudflare Worker deployment now routes 100% traffic to version `99f174d7-b228-4746-900d-210a6816de53` (version number 87), created at 09:47:23 UTC. It includes the folder-listing, version, audit and atomic bulk API routes. Worker bindings show the Supabase publishable key as a secret binding; no service-role key is configured in the Worker.
- Remaining acceptance gates: authenticated real-user upload/download/preview/version/trash/restore flows, two-user isolation, representative Myanmar/English OCR pilot, leaked-password protection review, and a verified review/remediation of the Dependabot/npm advisory set. A private-repository Dependabot alert listing was not available through the connected GitHub read endpoint in this check; no alert is claimed fixed.

- Deployment automation note: the Vercel GitHub Actions workflow's invalid job-level `secrets` condition was corrected to a step-level token check. The corrected run `36991704683` passed, but its deploy/build steps were intentionally skipped because the `VERCEL_TOKEN` GitHub secret is not configured. Vercel's connected Git integration subsequently produced deployment `dpl_94Z3TeFYrkfxTZo7XBhziJ2FGSoQ` for commit `1b6ac3a5`; do not interpret the workflow's successful token-check run as a deployment.


### Folder filters, atomic bulk and batch queue — 2026-10-02

- Added `GET /api/folders` for distinct active folder paths scoped to the authenticated owner and a matching folder filter in Cloud Documents.
- Bulk status and Trash now call one atomic database RPC for up to 100 unique IDs. It validates every document before updating and writes audit events in the same transaction; no partial batch is applied.
- Added sequential multi-file upload queue with 50 MiB per-file checks, per-file queued/uploading/complete/failed states and retry of failed items. Byte-level progress and resumable chunk upload remain open.
- Added Vercel production deploy workflow using a pinned CLI and the existing project/team IDs. The workflow ran successfully but skipped deployment because the GitHub Actions `VERCEL_TOKEN` secret is not configured; production still needs that secret before new frontend code can be published automatically.
- Cloudflare Worker version 87 is receiving 100% traffic, so the folder-listing, atomic bulk and version API changes are deployed. Real authenticated browser acceptance remains open.


### Latest runtime rollout — 2026-10-02 09:51 UTC

- Cloudflare Worker version `99f174d7-b228-4746-900d-210a6816de53` (version number 87) is receiving 100% traffic. This version was uploaded after the folder-listing, atomic bulk and version-audit Worker changes were committed.
- Supabase schema/function checks confirm the version table, owner-scoped RLS policies and RPC permissions. `anon` cannot execute the version or bulk RPCs; authenticated users can execute only the intended functions. Bulk updates rely on column-level grants and RLS.
- GitHub Actions `Doka Quality Checks` passed on commit `5ad3efa7`, including backend regression tests and frontend build/smoke tests. Local Core Checks passed on commit `0807b5c3`.
- Vercel production deployment `dpl_94Z3TeFYrkfxTZo7XBhziJ2FGSoQ` (commit `1b6ac3a5`) is READY. Its production JavaScript bundle was checked and contains Version history, safe preview, folder filtering and atomic bulk actions. It does not yet contain the later batch upload queue. The GitHub Actions deploy workflow skips without `VERCEL_TOKEN`; add that secret and manually run the workflow to publish the newest frontend commit.
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
