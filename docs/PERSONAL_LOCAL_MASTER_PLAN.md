> **Historical plan notice (2026-10-07):** This document preserves the original Personal Local feature decomposition and product intent. For current execution order, release gates, evidence status and the final path to sign-off, use `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`.

# Doka — Personal Local Master Plan

## Product direction

The current Doka product is being developed first as a **single-user local document organizer and DMS** for real office use and testing. Commercial/multi-user/cloud features are deliberately deferred until the personal edition is stable.

The core problem is a messy office drive containing old files, duplicated filenames, near-duplicates, different document versions, and mixed Myanmar/English content.

## Non-negotiable safety rules

1. Original source data is read-only.
2. The application writes only inside a dedicated working area.
3. Source data is copied before organization work begins.
4. Copy integrity is verified with hashes before processing.
5. The system never permanently deletes or overwrites source files as part of organization.
6. Uncertain files go to review/quarantine rather than being guessed.
7. AI recommends; the user approves.
8. Every rename/move/copy operation is logged and recoverable.
9. Large batch jobs are resumable after interruption.
10. Local/rule-based processing must remain useful when no AI API is configured.

## Target local flow

D:\OfficeFiles (ORIGINAL / READ ONLY)
→ Import/Copy Session
→ D:\DMS_Workspace (WORKING COPY)
→ Inventory + Hash
→ Text extraction/OCR (Myanmar + English)
→ Rule engine
→ Duplicate/version analysis
→ Optional AI recommendation
→ Review/Approve
→ Safe rename/move
→ Final organized library
→ Backup + audit history

## Doka delivery phases

A→E is the current delivery sequence: A) security hardening, B) local workflow usability, C) OCR/search quality, D) real-world pilot and tuning, E) later enterprise/cloud architecture. A phase is not considered complete merely because code exists; it must pass its relevant tests and, where applicable, real-machine validation.

## Implementation phases

### Phase 0 — Stabilize the existing repo
- Make local mode the default.
- Reduce dependency on MinIO/Redis/Celery for the basic personal workflow.
- Keep advanced features present but hidden/deprioritized.
- Centralize configuration and API behavior.
- Fix obvious auth/config inconsistencies.
- Establish smoke tests and repeatable local startup.

### Phase 1 — Safe workspace
- Source root registration.
- Read-only source policy.
- Working-copy creation.
- Copy manifest and SHA-256 verification.
- Quarantine and backup roots.
- Operation journal and recovery state.

### Phase 2 — File inventory
- Recursive scanner.
- File type, size, timestamps, path and hash.
- Empty/corrupt/unreadable detection.
- Filename collision groups.
- Large/old file reports.
- Scan progress and resumability.

### Phase 3 — Document understanding
- PDF/Word/Excel/image text extraction.
- Myanmar + English OCR.
- Metadata extraction using deterministic patterns first.
- Document type and language detection.
- Content fingerprints.

### Phase 4 — Duplicate/version intelligence
- Exact hash duplicates.
- Filename duplicates.
- Near-duplicates using local TF-IDF.
- Content/version groups.
- Difference summaries.
- Human review queue.

### Phase 5 — Safe organization
- Recommended folder.
- Recommended filename.
- Preview of all changes.
- Approve/edit/reject.
- Atomic/resumable operations.
- Undo/recovery.
- Full audit trail.

### Phase 6 — Search and daily usability
- Filename/content search.
- Filters by date/type/category/status.
- Document relationships.
- Dashboard.
- Saved searches.
- Bulk review.

### Phase 7 — Optional free-first AI
- AI disabled by default.
- Provider order is configurable.
- Try provider A; on timeout/rate-limit/model failure continue to B.
- Free-first providers before paid providers.
- Never require AI for core file safety.
- Track provider, model, latency and failure reason.
- Enforce configurable per-provider attempts/timeouts.
- Keep sensitive content handling explicit.

### Phase 8 — Real-world validation
- Test on a COPY of real D: data.
- Record false duplicate/version decisions.
- Tune rules and OCR.
- Add only features that solve observed problems.
- Keep a regression dataset of representative Myanmar/English documents.

### Phase 9 — Stable Personal Edition
Success means the user can run the system repeatedly on real office data without source-data risk, unexplained changes, or manual repair.

### Phase 10 — Commercial Edition (later)
Only after the personal edition is stable:
- multi-user/orgs
- stronger RBAC and tenant isolation
- managed Postgres/Supabase
- cloud storage
- remote backend
- Vercel/Render deployment
- monitoring
- billing/licensing
- product onboarding
- commercial support/security hardening

## Feature priority

### Build now
Scanner, working copy, hashes, OCR, inventory, duplicate/version analysis, review queue, safe organization, audit/recovery, local search, backup.

### Keep but hide/defer
SOP, reminders, advanced reporting, realtime, mobile, external integrations, enterprise RBAC, email, cloud storage.

### AI last
Classification, semantic search, content extraction, organization recommendations, document assistant.

## AI provider policy

The application uses a configurable provider chain rather than locking the product to one vendor. The default order is free-first and can be changed without code changes.

A provider failure must not fail the document workflow. If all providers fail, the application falls back to local/rule-based processing or marks the item for review.

## Future-proofing

The core document model should remain provider-neutral. AI results should store the provider/model/method and confidence, so the AI vendor can be changed later without rewriting document storage or organization logic.


## Web Access While Data Stays Local

The personal edition has two separate concerns:

- **Local data plane:** files, SQLite database, OCR workspace, backups, and organization operations remain on the home/office PC that owns the data.
- **Web interface:** the React/Vite frontend remains the browser UI for viewing, searching, reviewing, downloading, and later managing documents.

### Remote-office access

For access from another location, do not expose the FastAPI/React server directly to the public Internet during the personal phase. Prefer a private network/VPN overlay (for example, Tailscale) or an equivalent private tunnel.

Target flow:

Office browser
→ private secure connection (VPN/secure tunnel)
→ home PC React web server
→ local API
→ local database + local files

This keeps the original D: drive and working data local while still allowing browser access from the office.

### Data transfer rule

Viewing metadata should not require copying the whole D: drive. A document download is an explicit action from the web UI. The server should stream the requested file from the working/final library and log the download.

### Future cloud mode

When the personal edition is stable, the same frontend/API contracts can be moved to Vercel + Render + Supabase/object storage without deleting the local mode. Local and cloud storage should remain separate adapters behind the same document/storage interfaces.


## Recommended personal web setup

For development/testing on the home PC:

1. Start FastAPI on the home PC at port 8000.
2. Start the React app with `npm run dev:network` so it listens on the private network interface.
3. Use a private VPN/overlay such as Tailscale between the home PC and office device.
4. From the office browser, open the home PC's private VPN address on port 3000.
5. Keep the FastAPI API behind the Vite proxy; do not publish port 8000 directly.
6. Do not port-forward 3000/8000 from the home router during the personal phase.

The repository keeps both local and web code. Nothing is removed merely because a feature is not currently needed; advanced modules remain available for later activation.


## External Services / Deployment Boundary

The personal edition keeps the data plane local. External services are integration targets, not required dependencies for local operation.

- **Vercel**: React/Vite web frontend deployment target only; do not move the local document data plane to Vercel.
- **Render**: optional future remote FastAPI/worker deployment for a cloud edition; not required for the personal local edition.
- **Supabase**: optional future managed PostgreSQL/auth/storage target; do not migrate the local SQLite/workspace until the personal edition is stable.
- **Sentry**: recommended optional error monitoring integration; must never receive document contents, OCR text, file paths containing sensitive names, or secrets.
- **Private VPN**: required before office-to-home browser access; prefer a private network such as Tailscale rather than public port forwarding.
- **AI providers**: optional and disabled by default; provider order remains configurable and AI must not perform destructive filesystem operations without explicit user approval.

Integration rule: all external services must fail closed for the local data plane. The DMS must remain usable without Vercel, Render, Supabase, Sentry, or AI provider credentials.


## Current implementation status

The Personal Local Edition core is implemented and covered by repeatable CI checks.

Completed in the repository:
- safe read-only source import with verified SHA-256 copies
- resumable workspace sessions and inventory
- local text/PDF/image OCR understanding
- local DOCX and XLSX/XLSM extraction
- duplicate and likely-version review
- deterministic category/folder recommendations
- explicit approval before organization
- copy-only Final organization with no-overwrite conflicts
- organization audit and safe undo
- working-copy search and file preview/download boundaries
- workspace backup, SHA-256 verification, recovery-only restore, and retention
- AI disabled by default with configurable free-first provider fallback
- privacy-safe optional Sentry integration
- frontend Safe Workspace review UI
- backend/frontend local-core CI regression checks

Final validation still requires a real machine with the local runtime and a copy of representative office data. Browser verification cannot be substituted by unit tests; it should be run against the actual local frontend/backend before the first real-data pilot.

No branch is required for this work; the repository's default branch remains the implementation target.
