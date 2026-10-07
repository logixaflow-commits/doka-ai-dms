# Doka Architecture Reference

> **Owner:** How is Doka structured and where are its runtime boundaries?
> **Update when:** Architecture, runtime, workflow-engine, repository-boundary, or deployment-boundary decisions change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Release status, detailed testing procedures, secrets, provider credentials, or phase backlog.

## Product editions

Doka has three editions:
- **Personal Local:** active first-release path; local filesystem and OCR with no cloud dependency.
- **Personal Cloud:** authenticated cloud path using Supabase and the active Cloudflare Worker.
- **Enterprise:** deferred until tenant, membership, RBAC, isolation, audit and rollback gates are activated.

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

Runtime is React 19 + TypeScript + Vite 7 with FastAPI/Python 3.12 and local filesystem/OCR services. Personal Local must not require Supabase, Cloudflare, Vercel, Redis, MinIO or AI credentials.

Safety boundaries:
- SOURCE_ROOT and WORKING_ROOT are separate.
- ORIGINAL_READ_ONLY=true and ALLOW_SOURCE_WRITE=false.
- FINAL_ROOT and QUARANTINE_ROOT remain inside WORKING_ROOT.
- BACKUP_ROOT is separate.
- Recovery is isolated.
- Organization is copy-only.
- Approved plans are executed deterministically and integrity is checked.

## Personal Cloud architecture

```
Browser
  -> Supabase Auth identity
  -> React/Vite
  -> Cloudflare Worker: doka-ai-dms
  -> Supabase Postgres + RLS + private Storage
  -> provider-specific storage paths when explicitly enabled
```

The Worker derives ownership from the verified token. RLS and private Storage are independent defense-in-depth boundaries. Service-role credentials remain server-side.

Storage routing currently documented:
- Source <=50 MiB: Supabase private Storage.
- Source >50 MiB: Backblaze B2 when configured.
- Derivatives: Cloudinary when configured and healthy.
- Exports/archive/recovery path: Google Drive when explicitly configured.

Provider configuration is not equivalent to live-tested readiness.

## Canonical workflow boundary

`workflow.py` remains the canonical workflow engine for the workflow path. PostgreSQL is the durable workflow/run source of truth where that cloud workflow is enabled. Do not introduce a second workflow engine.

AI-assisted organization preserves:
**Reader -> Planner -> Human Approval -> Executor**

- Reader: read/OCR/metadata/duplicate-version clues; no writes.
- Planner: recommendations and plans; no destructive writes.
- Human Approval: required for publication-sensitive organization.
- Executor: deterministic approved actions only.

An optional legacy `agents/` pipeline remains separate from the canonical workflow engine.

## Repository boundaries

- `web-platform/backend/`: FastAPI runtime and services.
- `web-platform/frontend/`: React/Vite UI.
- `web-platform/tests/`: maintained application regression tests.
- `cloudflare_worker/`: active cloud API.
- `supabase/migrations/`: cloud schema migrations.
- `scripts/`: validation, benchmark and pilot utilities.
- `docs/`: active domain documentation.
- `archive/legacy/`: preserved historical material.
- `infrastructure/` and `mobile/`: deferred/preserved areas.

## Deployment topology

- Personal Local runs on the user's machine.
- Cloud API is the active Cloudflare Worker `doka-ai-dms`.
- Supabase provides Auth, Postgres/RLS and private Storage.
- Vercel is owner-paused and must not be reactivated without explicit authorization.
- No active Render runtime is verified.
