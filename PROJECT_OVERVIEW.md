# Doka Project Overview

## Product
Doka is a document-management product with three editions: Personal Local, Personal Cloud, and Enterprise. The current release priority is Personal Local first; Cloud verification follows; Enterprise is deferred.

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

Runtime: React 19 + TypeScript + Vite 7 frontend; FastAPI/Python 3.12 backend; local filesystem workspace; local authentication/state; Tesseract OCR. Personal Local must work without Supabase, Cloudflare, Vercel, Redis, MinIO, or AI credentials.

Safety boundaries: SOURCE_ROOT and WORKING_ROOT are separate; ORIGINAL_READ_ONLY=true; ALLOW_SOURCE_WRITE=false; FINAL_ROOT and QUARANTINE_ROOT stay within WORKING_ROOT; BACKUP_ROOT is separate; restore is isolated; organization is copy-only.

## Personal Cloud architecture
```
Browser -> Supabase Auth -> React/Vite -> Cloudflare Worker
        -> Supabase Postgres + RLS + private Storage
        -> provider-specific storage paths when explicitly enabled
```

Supabase Auth supplies identity. The Worker derives ownership from the verified token. RLS and private Storage remain independent ownership boundaries. Service-role credentials never belong in browser configuration.

Current storage routing: source objects <=50 MiB use Supabase; >50 MiB use B2 when configured; derivatives prefer Cloudinary when configured and healthy. Google Drive is a configuration-gated export/archive path. Real provider recovery is not claimed until live evidence exists.

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

When AI is enabled, keep Reader -> Planner -> Human Approval -> Executor separation. Reader and Planner have no destructive write authority. Executor accepts validated approved plans only.

## Deployment topology
- Personal Local: user's machine, FastAPI + React/Vite + local filesystem/OCR.
- Personal Cloud API: active Cloudflare Worker `doka-ai-dms`.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: owner-paused frontend target; do not reactivate without explicit authorization.
- Render: no active runtime is established.
