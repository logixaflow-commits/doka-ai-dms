# Doka Remediation Execution Log

Date: 2026-10-03

## SEC-001 — Secret scanning

- Added Gitleaks directory scanning to the existing consolidated `.github/workflows/doka-quality.yml`.
- Uses a version-pinned container image and read-only checkout mount.
- No additional workflow or runner job was created.
- Scan has not executed because recent GitHub Actions jobs completed with `runner_id=0`, no steps and no retrievable logs. No clean scan baseline is claimed.

## Regression test coverage

- Expanded the backend test command to run both `web-platform/backend` and `web-platform/tests`.
- This includes cross-cutting security, pilot, OCR, and backup helper tests rather than only the backend-local directory.
- Tests remain unverified until a runner can actually execute them.

## BE-009 / BE-010 inspection

- Active Personal Local Safe Workspace service uses per-session threading locks and temporary-file replacement for JSON state writes. Multi-process behavior and crash-recovery semantics still require tests.
- Legacy JSON document-versioning service is not registered in the Personal Local FastAPI entry point.
- Re-inspected lock/status references in active Safe Workspace service; no duplicate-return lock-status branch was found. No speculative code change made.

## CI evidence boundary

- GitHub push-triggered runs for commits `cd0334f` and `78f42da` failed within seconds with all jobs reporting `runner_id=0`, empty step lists and no retrievable logs. This does not establish a code/test failure; hosted runners did not execute the jobs.
- The latest run after expanding test coverage has not produced usable test evidence.
- Dependabot alert inventory remains inaccessible through connected repository permissions; the previously mentioned approximate count is not an itemized verified inventory.

## Prior SEC-014 implementation

- Added structural PostgreSQL URL parsing and shell-free `pg_dump` invocation in `web-platform/backend/app/core/backup_utils.py`.
- Updated legacy Celery database backup task and added parser tests in `web-platform/tests/test_backup_utils.py`.
- This hardens the legacy database backup path; Personal Local workspace archives still use `WorkspaceBackupService`.
- Tests have not been executed.
## Workspace backup destination isolation

- Review found that the workspace backup service resolved and created `BACKUP_ROOT` without rejecting overlap with the source or active workspace, and without rejecting a symlink at the configured backup root.
- Updated `_backup_root()` to reject symlink roots and any ancestor/descendant overlap with `SOURCE_ROOT` or `WORKING_ROOT` before creating the directory.
- Added regression coverage for nested paths, ancestor paths, safe external paths, and symlink roots in `web-platform/tests/test_workspace_backup_safety.py`.
- Tests have not been executed; CI remains skipped while hosted runners are unavailable. No runtime or office-pilot verification is claimed.
## Personal Local / Cloud API boundary

- Review found that the Personal Local FastAPI entry point imported and mounted the optional Supabase-backed `/api/storage` and `/api/documents` routers even though a separate `app.cloud_main` entry point exists for the Cloud API.
- Removed those cloud router registrations and imports from `app.main`; the cloud routes remain available through the dedicated cloud entry point only.
- Added `web-platform/tests/test_personal_local_entrypoint.py` to assert local auth/workspace routes remain and cloud routes are absent.
- This is an entry-point isolation change only; no cloud deployment was enabled. Tests have not been executed while CI is paused.
## Local authentication state file permissions

- The persistent SQLite revocation/refresh-state file is now set to owner read/write only (`0600`) on POSIX systems after opening, before schema access. This reduces the risk of another local OS account editing token revocation state.
- Added a POSIX-only regression test for the resulting file mode. Windows behavior is left to its native ACL model.
- The test has not been executed; runtime verification remains pending.
## CI dependency-audit duplication

- Re-inspection of `.github/workflows/doka-quality.yml` found two frontend `npm audit` executions: the JSON-report step already fails on any reported vulnerability, and a later clean-audit step repeated the same network audit.
- Removed only the redundant second audit invocation. The first full JSON audit/report and failure gate remain in place; no CI run was dispatched.
## Mandatory original-source read-only configuration

- Re-audit found the active import service rejected `ALLOW_SOURCE_WRITE=true` but did not independently reject `ORIGINAL_READ_ONLY=false` when source writes were otherwise disabled.
- The source validation gate now requires both `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false` before accepting a source directory.
- Added a regression test for the missing `ORIGINAL_READ_ONLY=false` case while preserving the existing explicit source-write rejection test.
- No original data was accessed or modified during this repository-only change. Tests remain pending execution.
## Organization output isolation from original source

- A deeper Apply-path review found that a misconfigured `FINAL_ROOT` could point outside `WORKING_ROOT`, including directly at `SOURCE_ROOT`, even though imported files were copied and hash-verified first.
- Apply now rejects a symlinked `FINAL_ROOT`, requires it to be a dedicated directory strictly inside `WORKING_ROOT`, and rejects any overlap with `SOURCE_ROOT` before creating output directories.
- Added a regression test that configures `FINAL_ROOT` as the original source directory and asserts Apply is rejected while source bytes and directory contents remain unchanged.
- This closes a configuration-dependent path to writing organization output into the original source. Test execution remains pending.
## Cross-platform backup archive path validation

- Restore validation now rejects control characters, empty/dot path segments, Windows alternate-data-stream colons, trailing dots/spaces, and reserved Windows device-name segments before extraction.
- Duplicate detection now uses case-folded normalized archive paths so case-colliding entries cannot overwrite one another on case-insensitive Windows filesystems.
- Added regression cases for case-colliding paths and reserved device names. Existing ZIP traversal, symlink, entry-count, size and compression-ratio checks remain.
- Tests have not been executed; this is code-level hardening pending local/CI verification.
## Local launcher Node engine alignment

- The frontend declares Node.js `24.x` in `package.json`, while both root launchers previously accepted any installed Node version and then failed later during install/build.
- Added an early Node major-version check to `start_application.bat` and `run.sh`; they now stop with a clear message unless Node 24.x is installed.
- These are static launcher edits only; Windows and POSIX startup have not been executed in this environment.

## Phase 0 — Frontend dependency metadata and local verification guide

- Compared the frontend `package.json` dependency declarations with the root package metadata in `package-lock.json`: lockfile version is 3, and declared dependency names/ranges match exactly (no missing, extra, or mismatched root declarations).
- This is a manifest/lockfile consistency check only. It is **not** an npm vulnerability audit and does not establish that Dependabot/npm audit findings are cleared.
- Rewrote `web-platform/backend/LOCAL_TESTING_GUIDE.md` to use the current repository paths, Python 3.12 CI baseline, Node.js 24.x frontend engine, current backend + repository regression command, and frontend lint/build/smoke commands.
- Added explicit copied-fixture/source-read-only/isolated-restore safety instructions and clarified that real-office pilot evidence must use a separate copy.
- No tests, lint, build, npm audit or office pilot were executed in this documentation/metadata review batch.
- Dependabot alert inventory remains unavailable through the connected GitHub capabilities; no individual alert has been declared fixed or accepted.

- Replaced the generic Vite-template `web-platform/frontend/README.md` with Doka-specific setup, edition flag, proxy, quality-command and source-data boundary guidance. No frontend source or dependency versions were changed.

## Phase 0–3 remediation code batch — 2026-10-03

- **BE-001 (legacy route hardening):** changed the retained legacy document upload route from a whole-file read/write to 1 MiB AnyIO streaming, enforces the existing 100 MiB cap during transfer, removes partial files on stream/DB-persist failure, and normalizes uploaded filenames to plain cross-platform names. This route is not mounted by the current Personal Local or dedicated Cloud API entry points; it is not evidence that active Cloudflare/Supabase uploads are resumable or larger than the current 50 MiB object limit.
- **BE-009 / BE-011 (legacy file version service):** added per-document filelock serialization for version creation and deletion, atomic metadata replacement with fsync + os.replace, cleanup of orphaned copied version files on create failure, and explicit VersionMetadataError instead of silently treating unreadable metadata as an empty history. Added a concurrent version creation regression test and corrupt-metadata test. This service is retained legacy code and is not the Personal Local workspace version store.
- Added filelock to backend requirements profiles that can load the legacy version service (requirements.txt, requirements-local.txt, requirements-production.txt, requirements-dev.txt, requirements-test.txt). No lockfile exists for these pip requirements; dependency audit must confirm the selected compatible release.
- **BE-010:** removed the unreachable duplicate return in the retained legacy document lock-status route. This does not alter the active Personal Local workspace lock service.
- **SEC-002:** added strict credentialed CORS origin validation to the separate cloud API entry point and enabled DELETE in its allow-method list. Added regression tests for wildcard, malformed, empty production and canonicalized origins. Live CORS headers remain unverified.
- **SEC-005 / AI-001 / AI cost guard:** external Hugging Face embedding calls now require both AI_ENABLED=true and explicit AI_EXTERNAL_PROCESSING_CONSENT=true. Document analysis now sends OCR text as a JSON-encoded untrusted-data field under a trusted system instruction that rejects embedded instructions; configurable AI_MAX_INPUT_CHARS (default 100,000; validated 1,000–1,000,000) limits input size. Added tests for consent, prompt boundary and size rejection. These tests have not been executed.
- **FE-001 / FE-004:** ThemeContext now guards storage access, validates persisted theme values, memoizes its context value/setter, and listens for system color-scheme changes with cleanup. Added frontend smoke assertions; lint/build/smoke have not been run.
- **SEC-006 / SEC-007:** extended the consolidated quality workflow with CodeQL for Python and JavaScript/TypeScript, a report-only Semgrep baseline artifact, and Syft SPDX JSON SBOM artifact. CodeQL upload does not itself prove branch protection blocks PRs; Semgrep is intentionally non-blocking until baseline triage. DAST is not configured because no approved staging target is available and Vercel production remains paused.
- **SEC-011:** added docs/DOKA_SUPABASE_SECURITY_REVIEW.md with source-level findings on document RLS, Storage path policies/no-overwrite, append-only versions, narrow version RPCs and audit table ACLs. Live database grants/policies, migration application state and two-user isolation remain unverified. The Worker audit helper is best-effort and can silently omit an audit event if the write fails; transactional audit guarantees remain open.
- No backend tests, frontend lint/build/smoke, npm/pip audit, CodeQL, Semgrep, SBOM workflow, browser E2E, DAST, live Supabase checks or office pilot were executed in this batch. Repository commits confirm source writes only.

## Mobile prototype stabilization — 2026-10-03

- Fixed a runtime import defect in AuthContext (useEffect was used but not imported), made stored-session restoration cancellation-safe, displayed a loading state until SecureStore restoration completes, and added best-effort server logout before clearing local credentials.
- Normalized mobile Expo DocumentPicker/ImagePicker result shapes into a validated React Native file descriptor, handles picker cancellation, infers common MIME types from legacy filenames, and passes the descriptor correctly through FormData. The API client now memoizes its Axios instance by session token, accepts EXPO_PUBLIC_API_BASE_URL, and returns the success shape expected by UploadScreen.
- Added Expo app configuration with purpose-specific iOS camera/photo-library descriptions and Android CAMERA/READ_MEDIA_IMAGES permissions, plus Node built-in tests for picker normalization and permission configuration.
- Changed the mobile test command to the cross-platform Node built-in test runner. A separate isolated Node 22.16 harness reproducing the nine pure picker/config assertions completed with 9 passed, 0 failed. This is not an Expo bundle, native build, device test, or full repository npm test run.
- Rewrote mobile README to identify the app as a legacy prototype and document the current API contract mismatch: its document endpoints are not mounted by the active Personal Local entry point, while the Cloud API uses Supabase Auth and a different contract.
- MOB-004 resumable/background upload remains blocked: the server contract currently provides no upload-session/chunk/commit API, and a client-only retry would restart the full upload rather than resume. MOB-002 image caching remains deferred because the current mobile screens do not render private document image previews; adding a cache before defining authorization, signed URL expiry and eviction would risk retaining private content.
- The mobile package remains Expo SDK 50 / React Native 0.73 with no committed lockfile. Do not upgrade individual native dependencies; perform a coordinated Expo SDK upgrade, lockfile generation and dependency audit before native builds.

## Phase 2–3 operations and QA artifacts — 2026-10-03

- **OPS-001:** replaced the retained production Dockerfile with a Python 3.12 multi-stage build, isolated virtual environment, minimal runtime packages, non-root doka user, health check and explicit source/config copies. Added backend .dockerignore rules to keep .env files, virtual environments, databases, backups and private office data out of the build context. Docker build/runtime have not been executed.
- **OPS-004 / QA-002:** added scripts/export_cloud_openapi.py and updated the consolidated backend CI job to emit an OpenAPI JSON artifact plus a coverage XML/terminal report. The coverage report is a baseline only; no threshold gate was introduced without an observed baseline. CI has not executed its steps.
- **DR-003:** expanded docs/PERSONAL_LOCAL_RUNBOOK.md with a copied-data backup/restore drill, manifest/hash comparisons, duration evidence and explicit RTO/RPO approval requirement. No real restore drill was run.
- The new CodeQL/Semgrep/SBOM/OpenAPI/coverage workflow changes were committed, but GitHub Actions automatic push runs continue to fail before exposing any steps/logs. No manual dispatch or rerun was made.

## CI runner evidence update — 2026-10-03

- Read-only inspection of the automatic push run for commit 0babf061fea1f2a3e40f7ead9bbc7262e572cac8 (run 37114338756) shows Backend regression tests, Backend dependency audit, Frontend build and smoke tests, and Static analysis and SBOM all concluded failure before any step records were available. The GitHub job records have steps=null and logs_url=null.
- Other automatic push runs for the same batch show the same missing step/log evidence; one superseded run was cancelled. These runs were triggered by repository pushes, not manually dispatched or rerun.
- The failure state is still inconclusive and cannot be attributed to tests, lint, dependency findings, CodeQL, Semgrep or SBOM generation. Keep all runtime verification statuses pending until a runner provides actual step output.

## SEC-001 secret-scanning developer guard — 2026-10-03

- Added a pinned Gitleaks v8.24.3 pre-commit hook in .pre-commit-config.yaml, matching the CI scanner version, and documented installation/use in docs/SECURITY.md.
- This adds staged-file scanning for contributors plus existing current-checkout CI scanning. It does not scan historical Git commits, and it does not replace GitHub Dependabot/Secret Scanning alert review. No pre-commit hook was installed or executed in this environment.

## CI runner evidence update — latest code commit

- Read-only inspection of automatic push run 37114518007 for commit e78d2353d639ce356d1c96d0e94f0663876e3fa8 shows all four jobs concluded failure with steps=null and logs_url=null. No command output is available; the run cannot establish test, audit, frontend, CodeQL or SBOM results.
- No manual workflow dispatch or rerun was performed. Keep runtime verification pending.

## Local setup, baseline and Safe Workspace concurrency — 2026-10-03

Environment and boundaries:
- Node.js 24.20.0 / npm 11.19.0; repository-local backend environment uses Python 3.12.13. The system Python is 3.14.5. The legacy Expo app remains SDK 50 / React Native 0.73 without a committed mobile lockfile.
- Frontend dependencies were installed with `npm ci` from the committed lockfile. Backend dependencies were installed in `web-platform/backend/.venv` from the local development requirements profile. No dependency manifest or lockfile was changed.
- `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false` were preserved. The interactive smoke used only a synthetic text fixture and disposable temp roots; its source SHA-256 was `4904B0500240FB28CA33A367D1CD65E8A67978228B5F51E7B878208C10FA1F7E`, and all 28 working copies matched. No original/office data was used.

Verification:
- Backend Personal Local suite: from `web-platform/backend`, `.venv\Scripts\python.exe -m pytest ..\tests -q` — **154 passed, 8 skipped, 10 warnings**, exit code 0. Skips include Windows symlink privilege limitations; warnings are FastAPI `on_event` and legacy `datetime.utcnow` deprecations. The configured suite intentionally does not collect the separate legacy Enterprise backend test tree.
- Earlier in this session: frontend `npm ci`, `npm run lint`, `npm test`, and `npm run build` passed; mobile utility `npm test` passed 9/9. These do not constitute a native mobile build.
- `npm audit` remains non-zero with five high findings. No blind upgrade/override was applied; resolution requires compatibility review (including the Tailwind major-version boundary).
- A disposable loopback UI smoke exposed concurrent status/list reads and `status.json` atomic replacement on Windows: observed `WinError 5` and one HTTP 500 on a polled status request. The interactive attempt issued 28 import POSTs; the cause of the repetition is unconfirmed. The source remained unchanged, but the complete browser workflow was not verified.
- After the lock fix, a controlled FastAPI TestClient run passed health, import/status/list, scan, local understanding/read, plan, explicitly confirmed apply, backup creation/verification, restore into isolated Recovery, and undo. The synthetic source hash was unchanged; restore did not overwrite active Final, and undo did not alter the Recovery copy. Auth was replaced only through an in-process test dependency override, so real local login/browser behavior remains pending.
- The first ad hoc TestClient harness invocation exited 1 with `SyntaxError` at a misplaced top-level `finally`; this was a harness syntax error, not an application failure. The corrected invocation completed successfully.

BE-009 follow-up:
- Protected `SafeWorkspaceService` status/list/search/inventory/understanding reads with the existing per-session lock used by imports, scans and other mutations. The understanding API now delegates to the locked service method.
- Added regression coverage confirming all five reader paths wait while a session lock is held. The full Personal Local suite above passes.
- Remaining limitations: this lock is process-local; cross-process coordination, crash recovery, and the full real-login browser walkthrough remain unverified.

Environment blockers and Git:
- Docker, Tesseract, Poppler, Gitleaks, Semgrep and pre-commit were unavailable. GitHub CLI was unauthenticated, so Dependabot inventory and detailed GitHub Actions logs remain unavailable. No live Supabase/two-user check, Docker image build, native mobile build, real-office pilot, or real restore/RTO/RPO drill was run.
- No GitHub Actions run was manually dispatched or rerun. No Vercel production configuration/deployment was changed.
- Work remains uncommitted on `main`; no commit or push was made. Review the complete working-tree diff before any future commit.


## CI and security remediation update — 2026-10-04

Direct-to-main changes (no feature branches or PRs):
- `5c7c2c6`: flush imported working-copy content before restoring source timestamps; update the session file-set assertion to include the two persistent coordination lock files.
- `20c70a0`: retain a redacted Gitleaks SARIF report as a short-lived CI artifact so findings can be triaged without exposing secret values.
- `51ec514` / `7b31993`: add encryption-key regression tests, remove the hard-coded Fernet fallback, require a valid explicitly configured `ENCRYPTION_KEY`, and document key generation in the environment template. Remove API-key-shaped credentials from the legacy AI integration guide and replace documentation token examples with placeholders.
- `cef69c8`: remove the unused, unavailable `unittest-xml>=0.7.1` test dependency that caused pip-audit to fail operationally.
- `0a4c19e`: keep frontend lint/build/smoke checks running even when npm audit reports findings; the job still fails after those checks if the audit remains non-zero.
- `6656007`: make the isolated symlink security job install only the test profile and run from the backend directory rather than installing the full ML/OCR runtime.

Verification from Doka Quality Checks run `37221393963` (commit `6656007`):
- Backend/repository regression suite: **290 passed, 11 warnings**.
- Symlink security suite: **3 passed**.
- Frontend install, lint baseline (0 errors), Vite production build (**1,817 modules transformed**) and frontend smoke suite all passed.
- Root dependency audit passed; all backend requirements-profile audits passed.
- Gitleaks: **no leaks found in the current checkout**. CodeQL, Semgrep baseline upload and SPDX SBOM generation completed successfully.
- The overall workflow remains failed only because the frontend npm audit still reports five high-severity package findings in the Tailwind development dependency chain. The underlying `braces` advisory affects versions through 3.0.3 and currently lists no patched release; npm proposes Tailwind CSS 4.3.3, a major upgrade. Do not apply an unverified override. Tailwind v4 has a newer browser floor, so confirm supported browsers before migrating.
- Historical credential exposure is not removed by editing the current tree. Treat the provider credentials formerly documented in the legacy AI guide as compromised and rotate them; Git history rewriting remains unperformed pending explicit approval.
- Latest Vercel deployment for code-only/CI-only commits was cancelled by the configured ignored-build-step rule; this is not a failed Vite build. The previously READY production deployment remains on commit `e8a15c9`. No Vercel settings or production environment values were changed.
- Cloud Edition runtime still uses the existing Supabase-backed Worker. D1/Storj migration and infrastructure provisioning remain separate, unstarted work; no Cloudflare resources were created or changed in this batch.


## Cloud Edition D1/Turso groundwork — 2026-10-04

- Added an offline D1 metadata baseline with owner/organization-scoped documents, versions, explicit permissions, OCR chunks, append-only audit events, idempotent jobs and a transactional outbox. Chunk rows now require a version belonging to the same document; SQL triggers enforce this relationship on insert and update.
- Added a Turso sync-receipt migration for event-level idempotency. Apply the same metadata schema to Turso before adding receipts.
- Added a Python Worker D1 adapter that uses prepared statements and bound scalar parameters, with safe error wrapping and an atomic batch helper. It is intentionally not imported by the production Worker until a real D1 binding and staging migration are ready.
- Added offline SQLite schema tests and fake-binding adapter tests. CI run 37223169768 verifies the adapter tests and prior schema tests; the final chunk/version integrity guard is awaiting the next main-branch run.
- The active Cloudflare Worker continues to use Supabase Auth, Supabase PostgREST metadata and Supabase Storage. No D1 or Turso resources/bindings were provisioned and no live data was moved.
- D1 schema/adapter code is preparation only: SQLite and fake-binding tests do not replace remote D1 tests, authenticated multi-tenant isolation tests, Turso replay/recovery drills, or a production rollback rehearsal.
