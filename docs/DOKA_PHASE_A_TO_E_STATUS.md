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

The pilot gate hashes the supplied source copy before processing, imports and verifies a separate working copy, scans inventory and duplicate/collision groups, runs local document understanding/OCR, builds the organization review plan, creates a workspace backup, hashes the source copy again, and fails if the source changed.

Optional organization testing is explicit: python scripts/doka_pilot_check.py --source <COPY_OF_REAL_OFFICE_DATA> --require-ocr --apply-safe
Only proposals already classified as suggest_move are applied by that optional flag. Review/duplicate/version proposals are never auto-approved.

Pilot evidence to record:
- source file count and before/after source hash manifest;
- import verified/failed counts;
- OCR availability and representative Myanmar/English results;
- exact duplicate and likely-version false positives;
- organization proposals accepted/rejected;
- backup SHA-256 and recovery result;
- browser workflow result;
- regression fixtures added after tuning.

Phase D release gate: representative real-machine validation passes without source mutation and without unexplained organization changes.

## Phase E — Future enterprise/cloud architecture
Phase E is intentionally architecture-only until Phase D passes.
- Local filesystem + local SQLite/workspace remain the Personal Local data plane.
- React/Vite remains the web UI.
- Vercel is a future frontend deployment target.
- Render is a future remote FastAPI/worker target.
- Supabase is a future managed database/auth/storage target.
- External services must remain optional and must not be required for local operation.
- Local and cloud storage should be separate adapters behind stable document/storage interfaces.
- AI provider identity/model/method/confidence should remain provider-neutral.
Do not migrate the Personal Local data plane to cloud infrastructure merely to satisfy Phase E. The enterprise edition starts after the local safety/workflow gate is proven.

## Current status
| Phase | Repository state | Final gate |
|---|---|---|
| A | Implemented + regression covered | Automated security tests |
| B | Implemented + regression covered | End-to-end local browser workflow |
| C | Implemented + regression covered | Representative Myanmar/English quality test |
| D | Pilot harness added | Real machine + copied office dataset |
| E | Boundary documented/deferred | Architecture review after D |

## Main-branch rule
All Doka work is committed directly to main as requested. No feature branch is required for this delivery sequence.