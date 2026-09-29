# Personal Local DMS — Master Plan

## Product direction

The current product is being developed first as a **single-user local document organizer and DMS** for real office use and testing. Commercial/multi-user/cloud features are deliberately deferred until the personal edition is stable.

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
