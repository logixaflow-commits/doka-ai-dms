# DOKA AI DMS — Master Roadmap & Systematic Execution Plan

**Project Type:** Standalone AI-Powered Document Management & OCR Suite  
**Platforms:** Vite/React Web App (`http://localhost:5173`), FastAPI Backend (`http://localhost:8002`), Electron Native Desktop App  
**Status:** In Active Development & Local Verification  
**Language Specification:** English (Standard Technical Documentation)  
**Last Updated:** October 2026  

---

## 1. System Architecture & Topology

DOKA AI DMS provides a zero-leakage, multi-platform document intelligence system supporting:
`Document Ingestion → OCR Preprocessing & Layout Analysis → Text Extraction (Burmese & English) → Vector Embedding & RAG → Rule Matching & Tagging → Granular Folder RBAC → Audit Trail & Long-Term Archival`.

```mermaid
graph TD
    subgraph Client Applications
        Web["React + Vite Web App<br/>Port 5173"]
        Desktop["Electron Desktop App<br/>Local Watcher & Native Scanner"]
        Mobile["Mobile Web Scanner<br/>Camera OCR Client"]
    end

    subgraph Backend Services
        API["FastAPI Backend<br/>Port 8002"]
        OCR["OpenCV + Tesseract / PaddleOCR<br/>Layout & Syllable Tokenizer"]
        RAG["ChromaDB / SQLite Vector<br/>Document Semantic Search"]
        DB[(SQLite / PostgreSQL<br/>dms.db)]
    end

    subgraph Storage Layer
        LocalFS["Local File Vault<br/>dms_uploads/"]
        R2["Cloudflare R2 / S3<br/>Encrypted Cloud Vault (Optional)"]
    end

    Web <-->|REST API| API
    Desktop <-->|Native IPC & REST| API
    Mobile <-->|Camera Upload REST| API
    API <--> DB
    API --> OCR
    API --> RAG
    API --> LocalFS
    API --> R2
```

---

## 2. Completed Milestones & Operational Proofs

- [x] **Decoupled Standalone Infrastructure:** Assigned dedicated ports (Web: 5173, API: 8002).
- [x] **Database & ORM Stabilization:** Configured absolute SQLite path `Office_DMS/database/dms.db`, established full ORM tables (Users, Documents, Folders, Permissions, SOP Templates, Rules, Audit Logs), and seeded initial admin credentials (`admin` / `admin123`).
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
- [ ] **Multi-Tenant / Multi-User Isolation Tests:** Execute automated integration tests verifying complete data isolation between regular users and administrative roles.
- [ ] **End-to-End Cypress / Playwright Regression:** Automate cross-browser and Electron E2E test suites covering file upload, OCR extraction, search, and permission enforcement.

---

## 4. Next Systematic Steps

1. **Step 1:** Run `verify_all_backends.py` and frontend test suite to ensure backend route coverage is 100% verified.
2. **Step 2:** Test Electron desktop app folder watcher connection with backend file import endpoint.
3. **Step 3:** Perform live multi-page PDF batch OCR extraction test.
