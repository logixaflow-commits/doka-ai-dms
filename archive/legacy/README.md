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

## Delivery roadmap

Start with `MASTER-ROADMAP.md` for the live status, 12 release gates and update reminders. The detailed execution plan and issue register remain in `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`. The documentation map is maintained in `docs/DOKA_DOCUMENTATION_INDEX.md`, including the active UI map, architecture, and tools/services boundary.

## First run
See `QUICKSTART.md` and `docs/PERSONAL_LOCAL_RUNBOOK.md`.

For Windows, the main launcher is `start_application.bat`.

No PostgreSQL, Redis, MinIO, Supabase, Render, Vercel, or AI API key is required for the Personal Local smoke test.

## Validation status
Automated repository checks cover Python compilation, frontend build/smoke tests, and the Personal Local safety regression suite.

**Real-machine validation is still a required release gate.** Before treating the Personal Local Edition as stable for the real D: drive, test it on a small representative copy and verify source immutability, import verification, Myanmar/English OCR, duplicate/version review, approved copy-only organization, backup/restore/undo, and the browser workflow.

## Deferred enterprise edition
Earlier enterprise/cloud implementation, mobile code, integrations, reporting, realtime features, infrastructure, and advanced AI are preserved, not part of the current Personal Local runtime.

## Development checks
`Doka Quality Checks` is the consolidated automatic CI workflow. `Local Core Checks` is retained for deliberate manual runs. Vercel production smoke remains manual-only while production is paused.

## Cloud Edition — current implementation
The Cloud Edition implementation is merged to `main` and is verified independently of the intentionally paused Vercel deployment.

Storage routing: <=50 MiB to private Supabase Storage; >50 MiB to B2; derivatives prefer Cloudinary when configured and healthy. Direct upload sessions keep document bytes out of the Worker. Google Drive is configuration-gated and requires real OAuth/recovery evidence.

## Vercel status
Vercel remains intentionally paused by the owner. Do not reactivate, reconnect, trigger a deployment, or change deployment settings unless explicitly requested.

## Final go-live gates
Authenticated lifecycle, two-user isolation, 50 MiB boundary, real B2/Cloudinary/Drive recovery, Myanmar/English OCR, backup/recovery RTO/RPO, Supabase leaked-password protection, and a clean Vercel build remain release evidence gates.

## Documentation rule
Do not create new finished/phase-status files. Keep canonical status in the roadmap/current-state hierarchy and historical plans in legacy/archive locations.
