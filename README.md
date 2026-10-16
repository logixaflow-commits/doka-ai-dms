# Doka

Doka is a safety-first document management system with three editions: **Personal Local**, **Personal Cloud**, and **Enterprise**.

## Current release focus

**Personal Local first.** The active release path is:

**copied source → verified import → scan/OCR → review → human approval → organized working library → backup/recovery**

The original source is read-only. Doka must not use the original source as a writable organization target.

Current status: the Personal Local coding foundation is implemented, but real browser acceptance, representative copied-office validation, OCR benchmarking and measured recovery evidence are still required. Cloud verification follows the Local release gates. Enterprise is deferred.

## Editions

- **Personal Local** — React/Vite + FastAPI/Python + local filesystem/OCR. Cloud services are not required.
- **Personal Cloud** — React/Vite + Supabase Auth/Postgres/RLS/private Storage + Cloudflare Worker.
- **Enterprise** — deferred until its own tenant, RBAC, security and acceptance gates are activated.

## Quick start & Development Ports

| Component | Target Port / Shell | Command |
|---|---|---|
| **Web Frontend** | `http://localhost:5173` | `cd apps/web-platform/frontend && npm install && npm run dev` |
| **Backend API** | `http://localhost:8002` | `cd apps/web-platform/backend && uvicorn app.main:app --port 8002 --reload` |
| **Desktop App** | Native Electron Window | `cd apps/desktop && npm install && npm start` |
| **Mobile App** | Native Camera Scanner | `cd apps/mobile && npm install && npm start` |

Windows one-click launcher scripts:
- `start-doka.bat` — Launches Backend (8002) and Web Frontend (5173).
- `start_desktop.bat` — Launches Electron Native Desktop Application connected to port 8002.

## Repository layout

- `apps/web-platform/frontend/` — React/Vite browser application (Vite on port 5173).
- `apps/web-platform/backend/` — FastAPI Local & Cloud runtime (Uvicorn on port 8002), SQLite `Office_DMS/database/dms.db`.
- `apps/desktop/` — Electron Native Desktop application with local folder scanning and native menu integration.
- `apps/mobile/` — Mobile Camera OCR document scanner client.
- `apps/web-platform/tests/` — Maintained backend and frontend regression test suite.

## Documentation map

| Document | Purpose |
|---|---|
| `CURRENT_STATE.md` | authoritative current status, evidence and next action |
| `PROJECT_OVERVIEW.md` | architecture and runtime boundaries |
| `ROADMAP.md` | release gates, phases and backlog |
| `docs/OWNER_LOCAL_CHECKLIST.md` | owner/local-only acceptance tasks and full future-work inventory |
| `UI_DESIGN_SYSTEM.md` | implemented UI/design/accessibility contract |
| `TOOL.md` | working, evidence and documentation protocol |
| `docs/SELF_AUDIT.md` | repository-local structural/evidence preflight |
| `docs/REPOSITORY_INFRA_AUDIT_2026-10-15.md` | dated GitHub/Vercel/Render/Supabase/Cloudflare findings and remaining-work checklist |
| `SECURITY.md` | security boundaries and verification rules |
| `docs/ARCHITECTURE.md` | detailed architecture reference |
| `docs/DEVELOPMENT.md` | development setup and contribution workflow |
| `docs/TESTING.md` | automated and release acceptance testing |
| `docs/DEPLOYMENT.md` | deployment topology and release evidence |
| `docs/OPERATIONS.md` | runtime operations and provider readiness |
| `docs/DATABASE.md` | schema, RLS and migration rules |
| `docs/API.md` | Cloud API contract |
| `docs/AI_RAG.md` | AI/RAG and agent boundaries |
| `docs/STORAGE.md` | storage routing and recovery |
| `docs/TROUBLESHOOTING.md` | recurring diagnostic and recovery guidance |

Historical material is preserved under `archive/legacy/` and existing legacy areas.

## Safety

- Keep original source data outside the writable workspace.
- `ORIGINAL_READ_ONLY=true`
- `ALLOW_SOURCE_WRITE=false`
- Keep source and working roots separate.
- Review organization proposals before approval.
- Use copied representative data for acceptance.
- Keep verified backups.

## Release rule

Green CI or implemented code is not enough for release. Follow `ROADMAP.md` and close each required gate with evidence.
