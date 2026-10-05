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

The local quality workflow runs automatically for relevant changes. A green local check does not imply a GitHub Actions run or production readiness; see the roadmap for the remaining verification gates.

## Next milestone
The code foundation is now in the **real-machine validation phase**. The next meaningful milestone is not another architectural rewrite; it is proving the safe workflow against representative office files and then tuning organization/search/OCR quality from those results.

## Cloud Edition — current implementation

The Cloud Edition is being brought online separately from Personal Local. The current implementation branch is
`feature/cloud-storage-routing`; it is **not merged to `main` automatically**.

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

Legacy multipart document/version upload routes now fail closed with HTTP 410 rather than buffering large files through the Worker.

### Cloud Worker environment

Required/important server-side bindings for the direct-storage path:

```env
SUPABASE_URL=https://jkobgssaqifzrqfirdfu.supabase.co
SUPABASE_STORAGE_BUCKET=doka-documents
SUPABASE_PUBLISHABLE_KEY=<Cloudflare secret>
DOKA_STORAGE_MAX_OBJECT_BYTES=52428800
DOKA_SINGLE_USER_EMAIL=<the one approved account>
DOKA_STORAGE_SESSION_SECRET=<32+ byte secret>
STORAGE_PROVIDER=hybrid

# B2 — required only when >50 MiB source storage is enabled
B2_ENDPOINT=https://s3.<region>.backblazeb2.com
B2_BUCKET=<bucket>
B2_KEY_ID=<application key id>
B2_APPLICATION_KEY=<application key secret>
B2_REGION=<region>
B2_QUOTA_BYTES=<configured safety ceiling>
B2_QUOTA_ALERT_RATIO=0.80
B2_QUOTA_BLOCK_RATIO=0.95

# Cloudinary — server-side only
CLOUDINARY_CLOUD_NAME=<cloud>
CLOUDINARY_API_KEY=<key>
CLOUDINARY_API_SECRET=<secret>
CLOUDINARY_LOW_CREDIT_THRESHOLD=5
```

Never put B2, Cloudinary, storage-session, Supabase secret/service-role, QStash or Sentry auth credentials in browser `VITE_*` variables.

### Frontend direct-upload settings

`VITE_API_BASE_URL` points to the Cloudflare Worker. The frontend computes SHA-256 in the browser, requests a storage session, uploads directly to the selected provider, and completes the session. The UI default upload ceiling is 5 GiB; the Worker remains the final enforcement point.

### B2 quota safety

Doka uses its own B2-backed document metadata usage as the application quota ledger. At the configured 80% projected threshold it emits a quota warning (and can POST a configured `B2_QUOTA_ALERT_WEBHOOK`). At 95% it blocks new B2 uploads. Google Drive fallback is intentionally **not claimed as active** until a real Google OAuth/provider configuration exists.

### Google Drive export / backup

Google Drive is the intended user-owned export/backup destination, but there is no connected Google Drive account-management tool in this environment. The application therefore must not pretend Drive export/restore is live. The remaining gate is real OAuth/token configuration plus an authenticated export/restore drill.

### Vercel status

Vercel remains **intentionally paused by the owner**. Do not reactivate or deploy it unless explicitly requested. Cloudflare Worker changes can be verified independently.

### Verification

Current feature-branch verification includes:

- Python compile of `cloudflare_worker/` and `shared/`.
- Cloud storage provider contract tests.
- B2 multipart and quota policy tests.
- Frontend `npm ci` and production `npm run build`.
- Supabase Security Advisor recheck after the version-RPC security migration.

Full production readiness still requires real authenticated browser E2E, real B2/Cloudinary credentials, Google Drive OAuth/export-restore proof, backup restore drill, OCR pilot, and final main-branch CI/release approval.
