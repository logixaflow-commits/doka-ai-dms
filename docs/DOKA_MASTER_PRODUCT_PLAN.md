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
| `/admin/cloud-documents` | CloudDocuments | Upload, list, status update, download |
| `/admin/workspace` | WorkspaceReview | Local workspace route; development/local boundary only, not a hosted cloud workspace |

The active router in `web-platform/frontend/src/App.tsx` currently mounts only these authenticated application pages. The production sidebar currently exposes Overview and Cloud documents; local workspace is intentionally hidden in production.

### 4.2 Cloud API actually deployed to Cloudflare

| Endpoint | Purpose | Frontend usage |
|---|---|---|
| `GET /health` | Worker health | Dashboard |
| `GET /api/config` | Edition and readiness flags | Dashboard |
| `GET /api/documents` | Owner-scoped search, status/folder filter, pagination, active/trash listing | Cloud Documents + Dashboard |
| `POST /api/documents` | Authenticated upload | Cloud Documents |
| `PATCH /api/documents/{id}` | Status, metadata, rename and folder-path update | Cloud Documents |
| `GET /api/documents/{id}/download` | Authenticated short-lived download URL; rejects trashed docs | Cloud Documents + Dashboard |
| `DELETE /api/documents/{id}` | Recoverable Trash (soft delete) | Cloud Documents |
| `POST /api/documents/{id}/restore` | Restore from Trash | Cloud Documents |

Cloud UI/API parity for the currently implemented list/search/filter/pagination, upload, download, status/metadata/rename/folder-path update, Trash and Restore endpoints is present at code level. The current frontend/Worker commits are being deployed; real authenticated end-to-end validation remains a release gate. A successful signed-in upload, update, download, and cross-user isolation test has **not** yet been completed in a real browser session.

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
- Document upload: Cloud Documents calls authenticated upload.
- Document list: Cloud Documents calls owner-scoped listing.
- Document download: Cloud Documents and Dashboard use download flow.
- Document status: Cloud Documents calls PATCH.
- Account isolation: enforced in Supabase RLS/Storage policy design; real two-user E2E is still pending.

### Not yet available as complete Cloud UI workflows

- Folder/tree organization and move/rename.
- Full-text search and advanced filters.
- Document preview and page-level navigation.
- Delete/trash/restore lifecycle.
- Version history and compare/restore.
- Bulk actions and batch upload queue/retry.
- Editable metadata fields beyond current status/metadata payload.
- User profile and password management inside Doka.
- Organization/team membership, roles and permission editor.
- Audit log and administrative analytics.
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
