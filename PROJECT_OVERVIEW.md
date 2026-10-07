# Doka Project Overview

## Product
Doka has three editions:
- **Personal Local:** active first-release path.
- **Personal Cloud:** authenticated cloud path.
- **Enterprise:** deferred until tenant, RBAC, isolation, audit and rollback gates are activated.

## Personal Local architecture
```
Original source (read-only)
  -> verified import/copy
  -> working workspace
  -> scan / OCR / metadata / duplicate-version analysis
  -> review plan
  -> human approval
  -> deterministic copy to Final
  -> backup
  -> isolated recovery / undo
```

Runtime: React 19 + TypeScript + Vite 7 frontend; FastAPI/Python 3.12 backend; local filesystem workspace; local authentication/state; Tesseract OCR.

Personal Local must work without Supabase, Cloudflare, Vercel, Redis, MinIO, or AI credentials.

Safety boundaries:
- SOURCE_ROOT and WORKING_ROOT are separate.
- ORIGINAL_READ_ONLY=true.
- ALLOW_SOURCE_WRITE=false.
- FINAL_ROOT and QUARANTINE_ROOT stay within WORKING_ROOT.
- BACKUP_ROOT is separate.
- Restore is isolated.
- Organization is copy-only.

## Personal Cloud architecture
```
Browser -> Supabase Auth -> React/Vite -> Cloudflare Worker
        -> Supabase Postgres + RLS + private Storage
        -> provider-specific storage paths when explicitly enabled
```

Supabase Auth supplies identity. The Worker derives ownership from the verified token. RLS and private Storage remain independent ownership boundaries. Service-role credentials never belong in browser configuration.

Storage routing is defined in `docs/STORAGE.md`: source objects <=50 MiB use Supabase, >50 MiB use B2 when configured, derivatives prefer Cloudinary when configured and healthy, and Google Drive is a configuration-gated export/archive path.

## Repository boundaries
- `web-platform/backend/`: FastAPI Personal Local runtime and supporting services.
- `web-platform/frontend/`: React/Vite UI.
- `web-platform/tests/`: maintained application regression tests.
- `cloudflare_worker/`: active Cloudflare Worker cloud API.
- `supabase/migrations/`: cloud schema migrations.
- `scripts/`: repository validation and pilot/benchmark utilities.
- `docs/`: active domain documentation.
- `archive/legacy/`: preserved historical documentation and retired material.
- `infrastructure/`, `mobile/`: preserved/deferred areas.

## Runtime boundaries
Personal Local is a local data-plane application. Personal Cloud is authenticated and provider-backed. Enterprise, mobile, multi-region, distributed job infrastructure, and advanced intelligence are deferred feature trains and must not become implicit dependencies of the Personal Local runtime.

## Workflow and agent boundary
The canonical workflow engine remains `workflow.py`; PostgreSQL is the durable workflow/run source of truth where that cloud workflow is enabled. Do not introduce a second workflow engine.

When AI is enabled, keep **Reader -> Planner -> Human Approval -> Executor** separation. Reader and Planner have no destructive write authority. Executor accepts validated approved plans only.

## Authority map
- Architecture details: `docs/ARCHITECTURE.md`
- Release/status: `CURRENT_STATE.md`
- Deployment/runtime: `docs/DEPLOYMENT.md`
- Database: `docs/DATABASE.md`
- API: `docs/API.md`
- AI/RAG: `docs/AI_RAG.md`
- Storage: `docs/STORAGE.md`
- Operations: `docs/OPERATIONS.md`
- Testing: `docs/TESTING.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
