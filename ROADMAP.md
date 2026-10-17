# DOKA AI DMS — Master Roadmap & Systematic Execution Plan

> **Latest production-acceptance checkpoint — 2026-10-17; current `main` SHA `db76c9cbc89d508f9333b980671fa9feb1dd3913`**
>
> - Production Cloudflare Worker version 738 and current-main deployment/live smoke passed. Health/config return 200, unauthenticated document listing returns 401, production CORS allows the canonical origin and does not reflect an untrusted origin.
> - Dedicated staging Worker is deployed with staging Supabase/D1 only. Latest staging deployment run [39046323682](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/39046323682) passed build/deploy/health/config/preview CORS GET and OPTIONS checks.
> - Vercel production is READY on the latest frontend-affecting main release (SHA `50de3584beb2469a5fced181b224a032537f9c89`); live homepage and JS return 200, and the bundle uses production Worker/Supabase only. Current Preview uses staging Worker/Supabase only.
> - Current-main Doka Quality Checks, Production CI/CD, CodeQL, Cloudflare production deploy, and Live Infrastructure Smoke passed. Independent checks: self-audit 23/23; Personal Local maintained regression 138 passed; cloud provider contracts 63 passed; frontend lint/build/smoke passed; npm install audit reported zero vulnerabilities.
> - **Gate 12 is BLOCKED.** Strict Myanmar/English OCR accuracy fails the unchanged thresholds; full browser approval/final-copy/backup/isolated restore and measured RTO/RPO are not evidenced; authenticated staging User A/B lifecycle/isolation and exact 50 MiB byte integrity are pending; staging B2/Cloudinary/Google Drive bindings and recovery tests are absent; four staging SECURITY DEFINER advisor warnings require authenticated ownership tests/review; production leaked-password protection is plan-blocked.
> - Render is intentionally unused; do not create a Render replacement for the Personal Local FastAPI runtime.
> - Do not apply staging RPC changes to production or mark Gate 12 complete until every required staging, provider, OCR, browser and recovery gate has evidence and rollback is reviewed.
>
---

## 2. Completed Milestones & Operational Proofs

- [x] **Decoupled Standalone Infrastructure:** Assigned dedicated ports (Web: 5173, API: 8002).
- [x] **Database & ORM Stabilization:** Configured absolute SQLite path `Office_DMS/database/dms.db` and established ORM tables (Users, Documents, Folders, Permissions, SOP Templates, Rules, Audit Logs). Local bootstrap authentication requires `BOOTSTRAP_ADMIN_PASSWORD` from local environment configuration (minimum 12 characters); no hard-coded default admin password is intended, and local password authentication is disabled outside development/local/test.
- [x] **Backend API & Health Verifications:** FastAPI `/health` endpoint operational (HTTP 200 OK). Mounted routers for documents, templates, rules, permissions, audit, and brain_soul.
- [x] **Advanced OpenCV OCR Preprocessing:** Integrated deskewing, Contrast Limited Adaptive Histogram Equalization (CLAHE), adaptive binarization, and Tesseract TSV bounding box parser with Myanmar Unicode syllable normalization.
- [x] **Web Frontend Platform:** Built complete document management interface, document previewer with OCR bounding box overlay, and routed admin pages (`/admin/templates`, `/admin/rules`, `/admin/permissions`, `/admin/audit`). Frontend production build verified (passing in 9.02s).
- [x] **Desktop Native Client:** Built Electron desktop application (`apps/desktop`) with native system tray, menu bindings, and multi-window shell.
- [x] **Mobile Camera Scanner:** Added camera capture and upload workflows in `UploadScreen.js`.

---

## 3. Comprehensive Remaining Tasks (Consolidated from Legacy Backlogs)

### Priority 1: OCR Pipeline & Multi-Language Accuracy
- [ ] **Dual-Engine Benchmark:** Implement automatic fallback between local Tesseract OCR (with `mya` + `eng` language packs) and PaddleOCR for degraded scans.
- [ ] **Batch PDF Multi-Page OCR Queue:** Build asynchronous background worker to process large multi-page PDF documents page-by-page with live progress updates.
- [ ] **Bounding Box Interactive Correction:** Allow users to adjust, resize, or delete OCR bounding boxes and edit recognized text directly in the Web Previewer canvas.

### Priority 2: Storage Routing & Hybrid Cloud Modes
- [ ] **Storage Routing Execution:** Implement deterministic fallback between `STORAGE_PROVIDER=local`, `STORAGE_PROVIDER=r2`, and `STORAGE_PROVIDER=hybrid`.
- [ ] **SHA-256 Checksum Immutability:** Verify automated document hash generation on upload and reject corrupted or tampered file revisions.
- [ ] **Automated Backup & Retention Schedule:** Enforce configurable retention policies, automated document archiving, and one-click database export/restore.

### Priority 3: Desktop Native File Watcher & Mobile Integration
- [ ] **Native Electron Folder Watcher:** Connect Node.js `chokidar` folder watcher in Electron to auto-detect and upload newly added local files to the backend.
- [ ] **Desktop Native Offline Mode:** Enable local SQLite cache synchronization so desktop users can view cached document indexes while offline.
- [ ] **Mobile Document Scanner Enhancements:** Add automatic document edge detection, perspective warping, and auto-crop before uploading.

### Priority 4: Rules Engine & Automated Compliance
- [ ] **Rule Action Execution:** Wire up the rule manager to automatically apply tags, move documents to target folders, and dispatch webhook notifications when OCR keywords match.
- [ ] **Granular Folder Permissions Enforcement:** Enforce user role permissions (`read`, `write`, `admin`, `none`) across document download, rename, and delete endpoints.
- [ ] **Comprehensive Audit Trail Reporting:** Provide CSV/PDF export of document access history, user login events, and administrative configuration changes.

### Priority 5: Security Hardening & E2E Validation
- [ ] **Multi-Tenant / Multi-User Isolation Tests:** Execute authenticated staging HTTP integration tests with distinct User A/User B JWTs. Staging SQL RPC isolation checks pass, but live API isolation evidence is still required.
- [ ] **End-to-End Cypress / Playwright Regression:** Complete the real browser approval → final copy/apply → backup → isolated restore/undo flow and capture evidence; automated smoke/build tests alone do not close this gate.

---

## 4. Next Systematic Steps

1. **Step 1:** Run `verify_all_backends.py` and frontend test suite to ensure backend route coverage is 100% verified.
2. **Step 2:** Test Electron desktop app folder watcher connection with backend file import endpoint.
3. **Step 3:** Perform live multi-page PDF batch OCR extraction test.


## 5. Release Gates and Evidence Status

The following gates are tracked explicitly so repository checks cannot mistake implementation notes for production acceptance. Gates remain **pending** until their required evidence is recorded; passing CI alone does not close them.

- **Gate 3 — Release readiness:** current release gate report and explicit readiness evidence.
- **Gate 4 — Regression acceptance:** maintained backend/frontend regression suites pass.
- **Gate 5 — Source integrity:** source immutability and recovery verification evidence.
- **Gate 6 — Recovery objectives:** recovery test and measured RTO evidence.
- **Gate 8 — Prerequisite gates:** Gates 1–7 are accepted with evidence.
- **Gate 9 — Authenticated cloud acceptance:** live cloud acceptance run, including its gate readiness and two-user isolation result.
- **Gate 10 — Tenant isolation:** distinct staging User A/User B tests prove cross-user data is not exposed.
- **Gate 11 — Provider recovery:** evidence covers Supabase Storage, B2 recovery, Cloudinary application path, Google Drive recovery, and the exact 50 MiB boundary.
- **Gate 12 — Production sign-off:** explicit sign-off after Gates 8–11 are evidenced; this is not inferred from CI.

### Immediate release blockers

- [ ] Re-run all CI workflows after the latest remediation and resolve any remaining failures.
- [x] Deploy the Worker changes to staging; staging health, API configuration, preview-origin CORS GET header and OPTIONS preflight smoke passed.
- [ ] Create two disposable staging Supabase users, add their email/password and staging publishable-key secrets, then run Authenticated Cloud Acceptance. Run Staging Cloud Provider Acceptance after configuring staging-only B2 and Google Drive credentials.
- [ ] After the authenticated staging gates pass, apply the RPC migration through a controlled production rollout, verify Worker/Vercel/database behavior, and record rollback evidence before marking Gate 12 complete.
- [ ] Supply disposable staging User A/B email/password secrets and `SUPABASE_STAGING_PUBLISHABLE_KEY` (the workflow mints fresh JWTs). Configure staging-only B2, Cloudinary and Google Drive bindings on the staging Worker; Render is intentionally unused for the Cloudflare Worker runtime.
