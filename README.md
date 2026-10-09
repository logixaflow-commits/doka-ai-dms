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

## Quick start

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and [docs/TESTING.md](docs/TESTING.md).

For Windows, the local launcher is `start_application.bat`.

Personal Local development requires a strong `BOOTSTRAP_ADMIN_PASSWORD`; no usable default password is shipped.

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
