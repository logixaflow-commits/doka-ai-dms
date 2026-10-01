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
- Optional Sentry telemetry is scrubbed of request data, cookies, authorization headers, breadcrumbs, contexts, and sensitive document paths.
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
| A | Implemented + regression covered | Automated security tests (green on latest main CI) |
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
- Python API hosting is still deliberately unselected; Vercel is the frontend host, not the Python OCR runtime.
