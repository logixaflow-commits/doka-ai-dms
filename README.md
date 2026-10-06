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

The consolidated phase plan and full remediation issue register are maintained in [Doka Unified Remediation Roadmap](docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md). It supersedes the old split phase ordering for execution while preserving the original remediation issue IDs and the Personal Local safety gates.

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

In Personal Local development mode, sign in with `LOCAL_ADMIN_USERNAME` (default: `admin`) and a strong `BOOTSTRAP_ADMIN_PASSWORD`. Local HS256 sessions are used when valid Supabase credentials are not configured; the placeholder values in the example files do not activate cloud authentication. No usable default password is shipped.

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

The local quality workflow runs automatically for relevant changes. A green local check does not imply production readiness; see the roadmap and final verification gates below.

## Cloud Edition — current implementation

The Cloud Edition implementation is merged to `main` and is being verified independently of the intentionally paused Vercel deployment.

### Cloud storage routing

- Source documents **<= 50 MiB** → private Supabase Storage.
- Source documents **> 50 MiB** → Backblaze B2.
- B2 objects **> 5 GiB** use S3 multipart upload sessions; file bytes do not pass through the Worker.
- Preview/thumbnail/cover derivatives **< 10 MB** prefer Cloudinary when configured and healthy.
- Cloudinary low/unknown credits fail closed and fall back to Supabase for derivative storage.
- `STORAGE_PROVIDER=mock` is reserved for local contract testing; `hybrid` is the production routing mode.
- Existing Supabase objects remain untouched by the metadata migration. Rollback is `STORAGE_PROVIDER=supabase`.

### Direct-upload security boundary

The Cloudflare Worker does **not** proxy document bytes. The browser requests a short-lived, HMAC-bound upload session, uploads directly to Supabase/B2/Cloudinary, then calls a small completion endpoint that verifies the issued session, size and provider result before writing metadata.

Legacy multipart document/version upload routes fail closed with HTTP 410 rather than buffering large files through the Worker.

### Google Drive export / backup

Google Drive is implemented as a configuration-gated user-owned export path. Production readiness is **not** claimed until real OAuth credentials are configured and an authenticated export + recovery drill succeeds.

### Vercel status

Vercel remains **intentionally paused by the owner**. Do not reactivate, reconnect, trigger a deployment, or change deployment settings unless explicitly requested. The repository has **no `vercel.json` override file**; build/install/output command overrides are not committed to the repository.

### Merge / branch status

The final Cloudflare/Vercel reconciliation changes and the previously approved PR changes are on `main`. PR #17 was merged and PR #19 was reconciled into `main` and closed. The remaining `fix/*` branches are historical working branches and may be deleted by the repository owner after confirming this `main` state:
- `fix/cloudflare-build-import-topology`
- `fix/cloudflare-build-import-topology-v2`
- `fix/cloudflare-final-bundle`
- `fix/cloudflare-production-origin`
- `fix/quality-checks-after-cloudflare-build`

### Final go-live gates

The project is **not yet signed off as production-ready**. Remaining proof gates are:
1. authenticated signed-in user workflow: upload/list/update/download/version/restore/trash;
2. two-user isolation test with separate sessions;
3. 50 MiB upload boundary test;
4. real B2, Cloudinary, and Google Drive export/recovery drills;
5. Myanmar + English OCR representative benchmark;
6. backup → restore → SHA-256 recovery proof and measurable RTO/RPO;
7. Supabase leaked-password protection enabled and verified;
8. one clean Vercel build after the current rate-limit window clears, without repeatedly retrying builds.

These are verification gates, not reasons to weaken the existing safety boundaries.

## Next milestone

The code foundation and branch consolidation are complete. The next milestone is evidence-based release validation: run the remaining authenticated, isolation, provider recovery, OCR, backup, Supabase security, and Vercel checks, then issue final go-live sign-off only when all required gates pass.
