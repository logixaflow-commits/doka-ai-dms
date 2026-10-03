# Doka — Personal Local Document Organizer

## Product identity

**Doka** is the working product name for the Personal Local Document Organizer.

## Current goal
The repository is being finished first as a **Doka Personal Local Edition** for safe real-office testing.

**Original source → verified working copy → inspect/OCR → duplicate & version review → user approval → organized working library → backup/recovery**

The original source is treated as **read-only**. The application must never use the original source as a writable organization target.

## What is currently usable
- Safe recursive import into a separate working area with SHA-256 verification.
- Resumable import sessions and inventory scanning.
- Myanmar + English text extraction and OCR support.
- Local understanding for PDF/images, DOCX, XLSX/XLSM and common text encodings.
- Exact duplicate detection and filename/version-family review.
- Rule-based organization proposals with explicit human approval.
- Safe copy-to-Final behavior: no destructive move, no overwrite of different content.
- Audit journal and safe undo of unchanged copies.
- Workspace backup, SHA-256 verification, recovery-only restore and retention pruning.
- Filename/path/content search over the verified working copy.
- Local browser UI for login, Safe Workspace review and status.
- Optional AI, disabled by default. When explicitly enabled, providers can be tried in configurable fallback order.

## Current architecture
- **Frontend:** React + TypeScript + Vite.
- **Backend:** FastAPI + Python.
- **Personal storage:** local filesystem + SQLite-compatible local configuration.
- **OCR:** Tesseract with English/Myanmar language support.
- **Remote office access:** intended through a private VPN/tunnel such as Tailscale, not public port forwarding.
- **Cloud services:** not required for the Personal Local Edition.

## Safety rules
1. Keep the real source drive outside the application workspace.
2. Set `ORIGINAL_READ_ONLY=true`.
3. Keep `ALLOW_SOURCE_WRITE=false`.
4. Keep `SOURCE_ROOT` and `WORKING_ROOT` separate; the backend rejects overlap.
5. Review organization proposals before approving them.
6. Start with a small copied test folder before using the real office source.
7. Keep regular workspace backups.

## First run
See `QUICKSTART.md` and `docs/PERSONAL_LOCAL_RUNBOOK.md`.

For Windows, the main launcher is `start_application.bat`.

The launcher starts the local backend on `127.0.0.1:8000` and the Vite frontend on `127.0.0.1:3000`.

No PostgreSQL, Redis, MinIO, Supabase, Render, Vercel, or AI API key is required for the Personal Local smoke test.

## Configuration
The template is `web-platform/backend/.env.example`.

Important local settings:
```env
SOURCE_ROOT=
WORKING_ROOT=./Office_DMS/Workspace
FINAL_ROOT=./Office_DMS/Workspace/Final
QUARANTINE_ROOT=./Office_DMS/Workspace/Quarantine
BACKUP_ROOT=./Office_DMS/Backups
ORIGINAL_READ_ONLY=true
ALLOW_SOURCE_WRITE=false
AI_ENABLED=false
```

Set a strong `BOOTSTRAP_ADMIN_PASSWORD` before the first login. No usable default password is shipped.

## Validation status
Automated repository checks cover Python compilation, frontend build/smoke tests, and the Personal Local safety regression suite.

**Real-machine validation is still a required release gate.** Before treating the Personal Local Edition as stable for the real D: drive, test it on a small representative copy and verify:
- source remains unchanged;
- import verification succeeds;
- Myanmar/English OCR works on representative files;
- duplicates and version families are reviewable;
- approved organization copies only into the workspace;
- backup/restore and undo behave as expected;
- browser workflow works end-to-end.

## Deferred enterprise edition
The repository still contains the earlier enterprise/cloud implementation, mobile code, integrations, reporting, realtime features, infrastructure, and advanced AI.

They are **preserved, not part of the current runtime**.
- `archive/legacy-enterprise/` — preserved legacy/enterprise material.
- `infrastructure/` — deferred deployment/infrastructure reference material.
- `mobile/` — preserved mobile application.
- `docs/` — current Personal Local documentation plus retained references.

Do not re-enable deferred modules in the Personal Local runtime unless they are intentionally brought back in a later phase.

## Development checks
`Doka Quality Checks` is the consolidated automatic CI workflow for relevant source changes. `Local Core Checks` is retained for deliberate manual runs only; the Vercel production smoke check is also manual-only while production is paused.

The project does not require a feature branch for this local-first workflow; changes are intentionally kept on the default branch as requested.

## Next milestone
The code foundation is now in the **real-machine validation phase**. The next meaningful milestone is not another architectural rewrite; it is proving the safe workflow against representative office files and then tuning organization/search/OCR quality from those results.
