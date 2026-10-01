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
- Live Supabase project now has `public.doka_documents`, `public.doka_document_versions`, a private `doka-documents` Storage bucket (50 MiB per-object cap), owner-scoped RLS policies, and Storage path policies. Four Doka migrations are applied and verified against the live project. Authenticated users can update only document `status` and `metadata`; object keys, hashes, and ownership are not updateable through table grants.
- Post-migration Supabase Security Advisor reports only the previously acknowledged leaked-password-protection warning; no other Doka security lint remains. Performance Advisor reports only unused indexes, expected before real data/query traffic exists.
- A free-cloud architecture decision is documented in `docs/DOKA_FREE_CLOUD_ARCHITECTURE.md`: Vercel for UI, Supabase Auth/Postgres, Supabase Storage initially, provider-neutral object storage with Cloudflare R2 as the larger-storage option, and a remote Python/OCR runtime to be selected only after Phase D workload measurements.
- Render Free is explicitly not selected as the durable Doka data plane because its filesystem is ephemeral.
- External services must remain optional and must not be required for local operation.
- Local and cloud storage should be separate adapters behind stable document/storage interfaces.
- AI provider identity/model/method/confidence should remain provider-neutral.
Do not migrate the Personal Local data plane to cloud infrastructure merely to satisfy Phase E. The enterprise edition starts after the local safety/workflow gate is proven.

## Current status
| Phase | Repository state | Final gate |
|---|---|---|
| A | Implemented + regression covered | Automated security tests (previously green; latest cloud-storage changes still need a confirmed CI run) |
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
- Cloud document metadata persistence: API and live database schema implemented; authenticated real-user upload/list/download verification remains outstanding.
- Remote OCR execution, real copied-office pilot, browser E2E, and downloadable thin client remain validation/integration work.
- Vercel project environment variables cannot currently be inspected or configured through the connected Vercel tools; frontend runtime API URL and Supabase public settings must be checked before production cloud use.
- Frontend Sentry React SDK integration is still pending; this frontend is Vite/React, so the supplied Next.js wizard command is not applicable. See `docs/DOKA_SENTRY_AND_CLOUDFLARE_SETUP.md`.
- Cloudflare R2 remains optional and is not activated; current Cloudflare onboarding requires an R2 subscription checkout before API token creation. Do not proceed if it requires a card or paid billing under the free-only project constraint.
- The latest observed READY Vercel production deployment still points to commit `f2b2c75` (provider inventory documentation); subsequent main commits have not yet appeared in the deployment list. Do not treat the current production deployment as containing the newest changes.
- The connected GitHub status tool returned no status records for the latest commits; do not claim the newest workflow run passed until its Actions result is confirmed.
- Python API hosting is still deliberately unselected; Vercel is the frontend host, not the Python OCR runtime.


## 2026-10-01 follow-up audit and hardening
- Fixed cloud upload compensation so a failed Storage PUT (including an already-existing object with Supabase `x-upsert=false`) never triggers deletion of that pre-existing object. Cleanup now runs only after this request's PUT completed successfully.
- Added focused regression tests for pre-existing object preservation, successful-request cleanup, and cleanup-error isolation.
- Hardened backend Sentry scrubbing to remove exception messages, frame locals/source paths, log messages, arbitrary tags, request payloads, and user-supplied transaction metadata while retaining safe exception type/function metadata.
- Added regression coverage for exception/stack-frame/log-entry scrubbing.
- Added `pytest-cov` to the local backend test dependencies and corrected backend pytest discovery to target the shared `web-platform/tests` directory with the backend app on the import path.
- These new tests have been committed but have NOT yet been executed in a clean runtime. Do not mark them green until a local/CI run is available.
- The GitHub Actions workflow-runs query for the latest audit commit returned no workflow runs. The Vercel commit status remains failed due to the reported build-rate limit; this is not a passing deployment.
- Frontend Sentry SDK/source-map integration remains pending because npm is unavailable in the connected repository-editing environment and the lockfile must be regenerated by npm (never hand-edited). The React Native wizard command is not applicable to the React/Vite frontend.
