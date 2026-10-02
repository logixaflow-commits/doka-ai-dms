# Doka — Master Product, Architecture & Delivery Plan

Last reviewed: 2026-10-02  
Repository: `logixaflow-commits/enterprise-ai-dms`  
Product name: **Doka**

## 1. Product purpose

Doka is intended to be a secure document-management workspace for personal and small-office use, with a path toward a later enterprise edition. The product should let a user safely bring documents into a workspace, verify and understand them, organize them with explicit human approval, find them again, and recover from mistakes.

The product's core principles are:

- **Protect originals:** source files are read-only; organization acts on verified copies.
- **Human approval:** proposed moves, classifications, and AI suggestions are reviewed before final changes.
- **Private by default:** each signed-in cloud user can access only their own documents; local documents remain on the user's machine.
- **Reliable recovery:** integrity hashes, audit records, backups, and tested restore paths are part of the workflow.
- **Useful without AI:** deterministic rules and ordinary search remain available when AI providers are disabled.
- **Free-first infrastructure:** do not enable paid billing or card-required services without an explicit decision.

## 2. Product editions and runtime boundaries

| Edition | Purpose | Current state |
|---|---|---|
| Personal Local | Local-first file intake, verification, OCR/extraction, review, organization, backup and recovery | Core implementation exists; real-machine pilot remains a release gate |
| Personal Cloud | Browser-based private cloud document library | Foundation deployed; authenticated end-to-end lifecycle still needs a real-user test |
| Enterprise | Multi-user organizations, roles, audit, policy, integrations and AI-assisted workflows | Historical code/UI fragments exist, but this is not a complete active production edition |

Do not mix these editions in navigation. A page must not appear as a working cloud feature until its API, permissions, data model, and end-to-end behavior exist in the deployed cloud runtime.

## 3. Current architecture

```text
Browser
  |
  +--> Vercel: React + TypeScript + Vite frontend
  |
  +--> Supabase Auth: sign-in and access tokens
  |
  +--> Cloudflare Worker (Python): Doka cloud document API
          |
          +--> Supabase Auth token verification
          +--> Supabase Postgres: doka_documents metadata + RLS
          +--> Supabase Storage: private doka-documents bucket

Personal Local runtime (separate boundary)
  |
  +--> FastAPI local application
  +--> local workspace / filesystem safety services
  +--> OCR and document extraction
  +--> organization review, backup and recovery
```

Key deployed services:

- Frontend: `https://enterprise-ai-dms.vercel.app`
- Cloud API: `https://doka.logixaflow.workers.dev`
- Supabase project: `jkobgssaqifzrqfirdfu`
- Private Storage bucket: `doka-documents`, 50 MiB object limit
- Worker configuration reports Supabase Auth and Storage as configured.
- Never expose a Supabase service-role key or AI provider secret in browser code.

## 4. Current implementation inventory

### 4.1 Frontend routes actually mounted in the active application

| Route | Component | Current role |
|---|---|---|
| `/login` | Login | Supabase sign-in/sign-up entry |
| `/admin/dashboard` | PersonalDashboard | Cloud health/config check, document counts/size, recent documents, download shortcut |
| `/admin/cloud-documents` | CloudDocuments | Upload, search/filter/paginate, rename, logical folder move, status update, preview, download, Trash/Restore/permanent delete, bulk status/Trash, version history/create/restore |
| `/admin/activity` | CloudAudit | Owner-scoped upload/download/preview/update/trash/restore/permanent-delete/version activity |
| `/admin/workspace` | WorkspaceReview | Local workspace route; development/local boundary only, not a hosted cloud workspace |

The active router in `web-platform/frontend/src/App.tsx` currently mounts only these authenticated application pages. The production sidebar currently exposes Overview and Cloud documents; local workspace is intentionally hidden in production.

### 4.2 Cloud API actually deployed to Cloudflare

| Endpoint | Purpose | Frontend usage |
|---|---|---|
| `GET /health` | Worker health | Dashboard |
| `GET /api/config` | Edition and readiness flags | Dashboard |
| `GET /api/documents` | Owner-scoped search, status/folder filter, pagination, active/trash listing | Cloud Documents + Dashboard |
| `GET /api/folders` | Owner-scoped distinct logical folder paths | Cloud Documents |
| `POST /api/documents` | Authenticated upload | Cloud Documents |
| `PATCH /api/documents/{id}` | Status, metadata, rename and folder-path update | Cloud Documents |
| `GET /api/documents/{id}/download` | Authenticated short-lived download URL; rejects trashed docs | Cloud Documents + Dashboard |
| `GET /api/documents/{id}/preview` | Five-minute signed URL for passive allowlisted formats only | Cloud Documents |
| `GET /api/documents/{id}/versions` | Owner-scoped version history | Cloud Documents |
| `POST /api/documents/{id}/versions` | Upload a new version and atomically preserve the previous object | Cloud Documents |
| `POST /api/documents/{id}/versions/{version_id}/restore` | Restore a prior version while snapshotting the current object | Cloud Documents |
| `GET /api/audit` | Owner-scoped activity log | Activity |
| `DELETE /api/documents/{id}/permanent` | Permanently remove only trashed docs and stored version objects | Cloud Documents |
| `DELETE /api/documents/{id}` | Recoverable Trash (soft delete) | Cloud Documents |
| `POST /api/documents/{id}/restore` | Restore from Trash | Cloud Documents |

Cloud UI/API parity for list/search/filter/pagination, upload, safe preview, download, status/metadata/rename/folder-path update, Trash/Restore/permanent deletion, version history/create/restore, bulk status/Trash and Activity is present at code level. The current frontend/Worker commits are being deployed; real authenticated end-to-end validation remains a release gate. A successful signed-in upload, update, download, and cross-user isolation test has **not** yet been completed in a real browser session.

### 4.3 Supabase foundation

- Supabase Auth is configured for the browser application.
- `public.doka_documents` and `public.doka_document_versions` are provisioned.
- RLS and owner-scoped Storage policies are installed.
- Storage bucket is private with a 50 MiB per-object limit.
- Authenticated users can update only approved columns: `status`, `metadata`, `filename`, `folder_path` and `deleted_at`; ownership, object key, content bytes and hash remain protected.
- Effective grants and relevant policies have been checked.
- Real signed-in multi-user isolation still requires an end-to-end test.

### 4.4 Personal Local foundation

The active local FastAPI application includes local authentication, workspace, workspace-file, cloud-document and cloud-storage route modules. The repository also contains services/tests for:

- Safe source/workspace/final/quarantine/backup path boundaries.
- Resumable import and SHA-256 verification.
- Inventory, duplicate/collision detection and review planning.
- PDF/image OCR and DOCX/XLSX/XLSM extraction.
- Search and metadata extraction.
- Human-approved copy-only organization and undo/audit journal.
- Workspace backup and isolated recovery verification.
- Optional privacy-scrubbed observability.
- AI disabled by default.

Phases A–C are implemented and have regression coverage according to the project status record. Phase D is **not complete** until the pilot is run against a separate copy of representative office data on the target machine.

### 4.5 Existing but not active production features

The repository contains additional components such as Document Detail, Document Upload, Documents, User Profile, Admin Users, Permissions, Analytics, Audit, Settings, Templates, Rules, Integrations, Monitoring, Semantic Search, AI Tagging and Versioning.

These must not be mistaken for production-ready cloud pages:

- Several are not mounted by the active `App.tsx` router.
- Several call legacy `/api/*` endpoints such as user/profile/admin APIs.
- The current Cloudflare Worker does not implement those legacy endpoints.
- Some correspond to the archived enterprise architecture or the separate local backend.
- They should be reintroduced only after their target edition and API contract are explicitly chosen and tested.

## 5. Current status and release blockers

| Area | Status | Evidence / remaining proof |
|---|---|---|
| Git repository structure | Implemented | Active code grouped under `web-platform/`; historical code under `archive/` |
| Local security foundation | Implemented + regression-covered | Still needs real-machine pilot evidence |
| Local OCR/extraction | Implemented in code | Myanmar/English representative quality test remains |
| Local organization workflow | Implemented in code | Browser/real-folder acceptance test remains |
| Local backup/recovery | Implemented in code | Phase D copied-data restore proof remains |
| Supabase Auth setup | Configured | Real sign-in session E2E remains |
| Supabase metadata + RLS | Provisioned | Two-user isolation test remains |
| Supabase private Storage | Provisioned | Real upload/download and size-limit test remains |
| Cloudflare Worker | Deployed | Health/config and invalid-token authorization checks have passed; authenticated CRUD E2E remains |
| Cloud UI | Search, pagination, rename, folder move, Trash/Restore added in code | Latest CI and production deployment + authenticated visual/E2E acceptance remain |
| Full admin/enterprise UI | Not active | Pages are unmounted and APIs are not deployed |
| Remote OCR runtime | Not selected | Decide only after Phase D workload measurements |
| Downloadable thin client | Planned | Build after cloud contracts are stable |
| AI provider workflows | Disabled / incomplete | Provider adapters, privacy controls, quotas and human review need implementation |
| Production browser E2E | Pending | Requires a real signed-in user session |
| Dependency audit | Follow-up required | Prior CI audit reported 8 npm findings (1 low, 1 moderate, 6 high); review patched versions and rerun CI |

## 6. Frontend / backend function coverage

### Available now in Cloud edition

- Sign in/out: Supabase Auth UI/session.
- Service status: Dashboard calls Worker health/config.
- Document upload/list/search/filter/pagination: owner-scoped Worker routes.
- Document rename/folder-path/status update: owner-scoped PATCH.
- Safe preview and download: short-lived signed URLs, with preview MIME allowlist.
- Trash, restore and confirmed permanent deletion with Storage cleanup.
- Version history, replacement upload and atomic restore via owner-checked database functions.
- Bulk status and Trash: single owner-scoped atomic database transaction for up to 100 documents.
- Activity: owner-scoped audit listing.
- Account isolation: enforced in Supabase RLS/Storage policies; real two-user E2E is still pending.

### Not yet available as complete Cloud UI workflows

- Rich folder-tree CRUD and folder-level permissions (logical folder paths are implemented).
- Server-side atomic bulk operations; current bulk status/Trash controls send per-document requests and are not atomic.
- Byte-level batch upload progress and resumable transfer (the sequential queue with per-file status and retry is implemented).
- Full-text content search and advanced metadata filters.
- Version comparison/diff and retention policy.
- User profile and password management inside Doka.
- Organization/team membership, roles and permission editor.
- Team-level audit export and administrative analytics.
- Cloud OCR/extraction and human review.
- Cloud backup/restore.
- AI classification, semantic search and provider controls.
- Integrations, templates, rules and notifications.

Do not show these as enabled controls until the backend endpoints and permission rules are implemented. For each feature, build the API contract first or in the same change, then wire the UI and add E2E tests.

## 7. Delivery roadmap

### Phase 0 — UI stability and verified cloud baseline

**Goal:** make the current cloud UI predictable, responsive and trustworthy.

- Complete desktop/tablet/mobile sidebar and content-layout verification.
- Ensure collapsed sidebar, mobile drawer, active route and tooltips behave correctly.
- Add consistent page header, breadcrumbs, loading, empty, error and success states.
- Test 320/375/390/768/1024/1440px widths with no overlap or horizontal overflow.
- Test keyboard navigation, visible focus, accessible labels and reduced-motion behavior.
- Run Vercel production deployment checks and confirm production commit.
- Run authenticated upload → list → status update → download with a real user.
- Test a second user cannot read, update or download the first user's document.
- Test file size boundary and failure cleanup.
- Keep local-only features out of cloud navigation.

**Exit gate:** browser acceptance passes on mobile and desktop; real authenticated cloud lifecycle and user isolation pass.

### Phase 1 — Complete core Cloud DMS

**Goal:** make Doka useful as a day-to-day cloud document library.

- Search by filename and metadata; filters for type, status and date.
- Document detail page with metadata and secure preview where supported.
- Rename and metadata editing with explicit validation.
- Folder/collection model and move operations.
- Delete to trash and restore (implemented); permanent deletion with object cleanup remains planned.
- Multi-file upload queue, progress, retry and cancellation.
- Bulk status and metadata actions.
- Version history model and download previous version.
- Storage usage view and clear quota/error messages.
- Audit events for upload, download, update, delete and restore.

**Exit gate:** all visible controls map to authenticated APIs, RLS tests and browser E2E.

### Phase 2 — Complete Personal Local pilot

**Goal:** prove the local-first workflow against representative documents.

- Run pilot only on a separate copy of real office data.
- Measure PDF/image OCR, Myanmar and English text quality.
- Validate DOCX/XLSX/XLSM extraction.
- Review duplicate/version detection false positives.
- Verify proposed folder structure with a human.
- Apply only explicitly approved safe-copy operations.
- Verify source hashes are unchanged.
- Create backup, restore to isolated directory and compare manifests.
- Record failures and add regression fixtures.

**Exit gate:** pilot passes without source mutation and with verified recovery.

### Phase 3 — Cloud/local convergence and thin client

**Goal:** share stable document contracts without coupling cloud storage to a local filesystem.

- Define provider-neutral document, metadata, storage and job interfaces.
- Keep Supabase Storage as initial personal-cloud object store.
- Keep R2 optional until quota/usage justifies it and free-only constraints are checked.
- Build authenticated job submission/status APIs for OCR and extraction.
- Select remote Python runtime only after Phase 2 workload and cost measurements.
- Build a thin desktop client for login, browse, upload/download, job review and local cache.
- Ensure cache loss never means source-document loss.

**Exit gate:** cloud and desktop clients share documented API contracts and data-integrity tests.

### Phase 4 — Team and enterprise foundations

**Goal:** introduce multi-user collaboration only after personal workflows are stable.

- Organization and membership data model.
- Role-based access control and document-level policies.
- Admin user management and invitation lifecycle.
- Immutable audit events and export.
- Retention, legal hold and lifecycle policies.
- Team-level search, collections and controlled sharing.
- Security review and tenant-isolation tests.

**Exit gate:** role matrix, tenant isolation, audit coverage and recovery tests pass.

### Phase 5 — AI and integrations

**Goal:** add optional intelligence without compromising privacy or user control.

- Provider-neutral model adapter and explicit provider/model selection.
- AI classification and metadata suggestions with confidence/provenance.
- Human approval before moving, renaming or changing access.
- Semantic search only after a measured need and privacy review.
- Per-user/org quotas, rate limits and cost visibility.
- Redaction/consent controls before external provider processing.
- Integrations (for example design, email or external storage) as optional adapters.
- AI remains off by default until these controls pass.

**Exit gate:** security/privacy assessment, provider failure handling, evaluation dataset and human-review E2E pass.

### Phase 4 / 5 design artifacts

- Enterprise identity, role matrix and tenant-isolation gates: `docs/DOKA_ENTERPRISE_RBAC_DESIGN.md` (design only; no team API is enabled).
- AI privacy, provider adapter, consent and human-review requirements: `docs/DOKA_AI_PRIVACY_AND_PROVIDER_DESIGN.md`.
- Personal Local external provider calls now require both `AI_ENABLED=true` and `AI_EXTERNAL_PROCESSING_CONSENT=true`; both default to false. A regression test blocks provider calls without consent.

## 8. Technical quality and operations backlog

- Resolve npm audit advisories through reviewed compatible updates; avoid blind major upgrades.
- Keep Dependabot updates and CI quality checks active.
- Add route-level component tests and Playwright/browser E2E for key flows.
- Add API contract tests for every UI action.
- Add structured, privacy-scrubbed error reporting.
- Add database migration checks and backup/restore drills.
- Add service/storage quota visibility and alerts that do not require paid add-ons.
- Keep secrets out of Git and browser bundles.
- Keep root directory clean; application code remains under `web-platform/`, current documentation under `docs/`, legacy under `archive/`.

## 9. Immediate next actions

1. Verify the sidebar layout change in a real browser at desktop and mobile widths.
2. Confirm the latest Vercel production deployment includes the sidebar fix.
3. Inspect and correct any remaining responsive overlap in Dashboard and Cloud Documents.
4. Perform a real signed-in cloud document lifecycle test; record evidence without exposing credentials.
5. Complete the two-user RLS/Storage isolation test.
6. Update the user-facing UI map so only live cloud capabilities appear in production navigation.
7. Start Phase 1 only after Phase 0 acceptance passes.

## 10. Definition of done for any future UI feature

A feature is complete only when all are true:

- The page is mounted in the active router.
- The navigation entry is visible only in the correct edition/role.
- The backend endpoint and request/response schema exist.
- Authentication, authorization and tenant/owner checks are enforced server-side.
- Loading, empty, error, success and disabled states are implemented.
- Desktop, tablet and mobile layouts are tested.
- Keyboard/accessibility basics are covered.
- Unit/API tests and browser E2E cover the main flow.
- Documentation and release notes are updated.
- Production deployment is verified against the intended commit.

---

**Project rule:** a component file, mockup, route returning the SPA shell, or API returning 401 for an invalid token is not proof that a complete user workflow works. Mark features complete only after authenticated end-to-end verification.


## 11. Work completed in the current delivery pass (2026-10-02)

- Stabilized the responsive sidebar shell; the production deployment for the sidebar commit reached READY.
- Added the cloud-library lifecycle migration: `deleted_at`, `folder_path`, owner/deleted/created index and least-privilege column update grants.
- Added Cloud Worker API support for filename search, status filter, active/trash listing, folder-path filter, rename, folder move, soft-delete and restore. Trashed files are excluded from normal listing and download.
- Added matching Cloud Documents UI actions for server-side search, pagination, rename, folder move, Trash and Restore.
- Added canonical JSON Schema at `shared/contracts/cloud-document.schema.json` and API/security contract at `docs/DOKA_CLOUD_API_CONTRACTS.md`.
- Latest observed GitHub Doka Quality Checks and Local Core Checks for commit `f787e38` passed; Vercel deployment for that commit reached READY; Cloudflare Worker build for that commit completed successfully.
- Browser Rendering hit the account rate limit during responsive inspection, so no new visual pass is claimed. Authenticated upload/update/download and two-user isolation still require a signed-in test session.
- Remaining Phase 0 gate: responsive browser acceptance at 320/375/390/768/1024/1440px, keyboard pass and real-user cloud lifecycle/isolation test.


## 12. Phase 3–5 supporting artifacts

- Canonical cloud document schema: `shared/contracts/cloud-document.schema.json`.
- Cloud API contract and security invariants: `docs/DOKA_CLOUD_API_CONTRACTS.md`.
- Enterprise RBAC and tenant isolation design: `docs/DOKA_ENTERPRISE_RBAC_DESIGN.md`.
- AI privacy and provider safety design: `docs/DOKA_AI_PRIVACY_AND_PROVIDER_DESIGN.md`.
- Phase 5 code safeguard: external provider calls require the independent consent flag in addition to the global AI enable flag; a test asserts no provider call occurs without consent.

## 13. Latest acceptance evidence — 2026-10-02

- Browser Rendering accessibility inspection of production Login at 390px confirms labelled email/password inputs, secure sign-in action and theme control are exposed to assistive technology.
- Production Login layout measurements: 390px viewport produced 390px document/body width; 1440px viewport produced 1440px document/body width. No horizontal overflow was detected on the Login page at those two sizes.
- This is not an authenticated dashboard/sidebar visual pass. The protected dashboard and Cloud Documents pages still require a real signed-in browser session before their responsive layout can be accepted.
- Doka Quality Checks run 36982859866 on commit 11fe7692c6d23412729dff7106d047fa598fe7c0 passed: 48 backend tests, TypeScript/Vite production build, and frontend smoke checks including cloud API schema/security checks.
- Local Core Checks passed on 36c14a39abbc6c9a3332ea4ab01fffd18ddfc25d and documentation-only follow-up f459c111d2c2378830df832ea698680854679a86.
- Vercel production deployment dpl_AGL7K8ejPDYx1rj9bZ6fWAHMMRhB is READY and owns https://enterprise-ai-dms.vercel.app.
- Cloudflare Worker build 9ab06efb-f44a-41e6-bc85-9345937d46a7 for f787e38cdec8463777012422fc2d8e0a4b9e773d completed successfully.
- Still open: eight npm audit findings (1 low, 1 moderate, 6 high); leaked-password protection disabled in Supabase Auth; real signed-in upload/list/rename/move/trash/restore/download; two-user isolation; real office-data OCR pilot; team/RBAC APIs; AI consent UX and redaction.


## 2026-10-02 implementation progress

The repository has moved beyond the original baseline described above. The following Phase 0/1 work is now implemented on `main`:

- Cloud library now includes recoverable Trash/Restore, filename search, status filtering, rename, logical folder-path move, and the existing secure download/upload flows.
- A new owner-scoped `doka_audit_events` table is enabled with RLS and narrow authenticated SELECT/INSERT grants.
- Cloudflare Worker now records upload, download, update, trash and restore events as best-effort audit side effects and exposes `GET /api/audit`.
- Frontend now has an Activity page and production navigation entry.
- The active cloud UI continues to keep local-only workspace/OCR operations outside the production cloud navigation.
- Production Vercel deployment for the lifecycle UI commit `e9018eb4` is READY.
- The repository's Phase A–E status document already records the broader existing contracts for free cloud architecture, AI privacy/consent, enterprise RBAC design, and provider-neutral storage.
- Supabase Security Advisor was rechecked after the audit-table change. The only reported security warning remains leaked-password protection being disabled.
- Full authenticated browser acceptance is still a release gate: a real signed-in account must exercise upload → list/search → rename/move → status update → download → trash → restore → activity, followed by a two-user isolation test.

### Updated Phase gates

**Phase 0 — UI/Cloud acceptance:** in progress. Code-level responsive fixes and cloud lifecycle controls are implemented; authenticated desktop/mobile browser acceptance is still required.

**Phase 1 — Core Cloud DMS:** in progress. Upload/list/search/filter/status/rename/folder/trash/restore/audit are implemented. Permanent deletion, object cleanup, preview, versions, bulk actions and richer folder-tree management remain.

**Phase 2 — Local pilot:** unchanged. Requires representative copied office data and Myanmar/English OCR measurements on the target machine.

**Phase 3 — Cloud/local convergence:** contracts and provider-neutral storage interfaces exist; remote OCR/job execution and thin client remain.

**Phase 4 — Enterprise:** RBAC/tenant-isolation design exists; production team APIs, membership lifecycle and enforcement are not active.

**Phase 5 — AI/integrations:** privacy/consent design exists; production AI job pipeline and optional integrations remain gated behind explicit provider configuration and human-review controls.

The project must not claim Phase 0–5 complete merely because contracts or UI components exist. Each phase closes only after its stated runtime/acceptance gate passes.


### 2026-10-02 follow-up — permanent deletion safety

- Added a permanent-delete endpoint that accepts only owner-owned documents already in Trash.
- The Worker enumerates version object keys and removes the current object plus version objects from the private bucket before deleting document metadata.
- If Storage cleanup fails, metadata is retained and the operation reports failure.
- Database DELETE is separately constrained by an owner-only RLS policy requiring `deleted_at IS NOT NULL`; normal active documents cannot be deleted through this privilege.
- Permanent deletion requires an explicit browser confirmation and is recorded as a `permanent_delete` audit event; the original document UUID is retained in event metadata after the document row is removed.
- The live Supabase migration was applied and its DELETE grant, restrictive RLS predicate and audit action constraint were verified.
- Remaining Phase 1 items: version creation/list/restore, atomic server-side batch APIs, richer folder tree and batch upload progress/retry. Safe inline preview is now available for PDF, common raster images, plain text and CSV; active formats such as HTML and SVG are rejected. Bulk status and move-to-Trash now use a single owner-scoped database transaction for up to 100 unique documents; the transaction validates all IDs before changing any rows and writes audit events atomically.
- Authenticated browser tests and two-user isolation remain mandatory release gates; code deployment alone does not close Phase 0/1.


### Cloud versioning implementation — 2026-10-02

- Added authenticated version history listing, replacement upload and restore endpoints to the Cloudflare Worker.
- New version upload preserves the prior object key as a version record and atomically switches the active document pointer through a SECURITY DEFINER function that validates `auth.uid()` and the parent document owner.
- Restore first snapshots the current document, then switches to the selected version in the same database transaction.
- Version objects remain private and are cleaned up by the existing permanent-delete workflow.
- Frontend exposes version history, 50 MiB replacement upload, per-version SHA-256/date/size and confirmed restore.
- Audit events include `version_create` and `version_restore`.
- Remaining release gates: authenticated browser acceptance and two-user isolation; these require separate real user sessions.


### Deployment verification — 2026-10-02 09:33 UTC

- Cloudflare Worker build for repository commit `1c9a8287` completed successfully and a new Worker deployment version is receiving 100% traffic. This includes the version history/create/restore API.
- Vercel production currently resolves to deployment commit `77be1bd0` (READY). The production JavaScript bundle contains bulk actions and safe preview, but does not yet contain the newly added Version history UI.
- Latest frontend source is committed and CI is passing; Vercel has not created a deployment for the subsequent frontend commits yet. Do not describe version controls as live in the production browser until the Vercel deployment is updated and the production bundle is rechecked.
- Authenticated end-to-end tests and two-user isolation remain open because no real signed-in test session is available in this run.


### Atomic bulk operations — 2026-10-02

- Added `POST /api/documents/bulk` for up to 100 unique documents.
- Bulk status updates and Trash execute through a single SECURITY INVOKER Postgres function under existing authenticated grants and RLS; all IDs are validated before any update, so partial batches are rejected.
- Audit events are inserted in the same transaction.
- Frontend bulk controls now call the single atomic endpoint rather than issuing parallel per-document requests.
- Added null-action validation, migration and regression/smoke coverage.


### Batch upload queue — 2026-10-02

- Added a multi-file sequential upload queue with per-file queued/uploading/complete/failed states.
- Failed files can be retried without re-uploading successful queue items; completed entries can be cleared.
- Every file is checked against the 50 MiB per-object limit before entering the queue.
- Byte-level transfer percentage, pause/resume and resumable chunk upload remain future work.


### Folder filters, atomic bulk and batch queue — 2026-10-02

- Added `GET /api/folders` for distinct active folder paths scoped to the authenticated owner and a matching folder filter in Cloud Documents.
- Bulk status and Trash now call one atomic database RPC for up to 100 unique IDs. It validates every document before updating and writes audit events in the same transaction; no partial batch is applied.
- Added sequential multi-file upload queue with 50 MiB per-file checks, per-file queued/uploading/complete/failed states and retry of failed items. Byte-level progress and resumable chunk upload remain open.
- Added Vercel production deploy workflow using a pinned CLI and the existing project/team IDs. The workflow ran successfully but skipped deployment because the GitHub Actions `VERCEL_TOKEN` secret is not configured; production still needs that secret before new frontend code can be published automatically.
- Cloudflare Worker deployment for the latest folder/bulk/version API changes is queued; only mark these APIs production-live after the build reaches success and 100% traffic is confirmed.


### Latest runtime rollout — 2026-10-02 09:51 UTC

- Cloudflare Worker version `99f174d7-b228-4746-900d-210a6816de53` (version number 87) is receiving 100% traffic. This version was uploaded after the folder-listing, atomic bulk and version-audit Worker changes were committed.
- Supabase schema/function checks confirm the version table, owner-scoped RLS policies and RPC permissions. `anon` cannot execute the version or bulk RPCs; authenticated users can execute only the intended functions. Bulk updates rely on column-level grants and RLS.
- GitHub Actions `Doka Quality Checks` passed on commit `5ad3efa7`, including backend regression tests and frontend build/smoke tests. Local Core Checks passed on commit `0807b5c3`.
- Vercel production deployment `dpl_94Z3TeFYrkfxTZo7XBhziJ2FGSoQ` (commit `1b6ac3a5`) is READY. Its production JavaScript bundle was checked and contains Version history, safe preview, folder filtering and atomic bulk actions. It does not yet contain the later batch upload queue. The GitHub Actions deploy workflow skips without `VERCEL_TOKEN`; add that secret and manually run the workflow to publish the newest frontend commit.
- Supabase Security Advisor still reports the intentional authenticated `SECURITY DEFINER` version RPCs and disabled leaked-password protection. The version RPCs explicitly validate `auth.uid()`, owner and user-scoped object paths; the warning is retained for review. The bulk RPC is SECURITY INVOKER.
