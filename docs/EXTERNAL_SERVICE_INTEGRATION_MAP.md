# External Service Integration Map

## Current personal/local edition

The application is intentionally usable without any external cloud service.

| Service | Current role | Connect now? | Later role |
|---|---|---|---|
| Vercel | React/Vite frontend hosting target | No | Host web UI only |
| Render | Optional FastAPI/worker hosting | No | Cloud backend/worker |
| Supabase | Optional managed PostgreSQL/auth/storage | No | Cloud database/storage |
| Sentry | Optional error monitoring | No | Sanitized application error telemetry |
| Tailscale/private VPN | Office browser access to home data plane | Later | Required for remote private access |
| AI providers | Optional recommendation layer | No | Gemini → OpenRouter → Groq → OpenAI fallback |

## Data-plane rule

Original files, working copies, OCR output, local SQLite, backups, and final organized files remain on the local machine in the personal edition.

No external service may become a required dependency for:
- safe import
- file hashing
- OCR
- duplicate/version analysis
- review
- organization
- backup/recovery

## Vercel

The existing Vercel project is retained as a future frontend deployment target. It should not receive the local document data plane.

Before activation:
1. Configure the project root as `app/`.
2. Configure only frontend-safe environment variables.
3. Point API traffic to the future backend endpoint.
4. Do not put local filesystem paths or document contents in Vercel environment variables.

## Render

Render should be introduced only when a cloud backend is actually needed.

Expected future services:
- FastAPI API
- Celery worker
- Celery Beat only if scheduled jobs are required
- Redis if asynchronous workloads require it

Do not deploy the personal local filesystem as a Render volume and treat it as the source of truth.

## Supabase

The existing Supabase project is retained but currently inactive.

Do not migrate the local SQLite database yet. When the commercial edition begins, define:
- PostgreSQL schema migration
- authentication model
- storage boundaries
- tenant/user authorization
- backup/restore strategy

## Sentry

Sentry is an observability target, not a document store.

When enabled, sanitize:
- document contents
- OCR text
- access tokens
- API keys
- full local file paths where sensitive
- request bodies containing documents

Only operational metadata and safe error context should be sent.

## Private office access

Use a private VPN such as Tailscale between the home data-plane machine and authorized office devices.

Do not expose FastAPI, SQLite, file preview/download endpoints, or the workspace filesystem directly to the public Internet.

## AI

AI remains disabled by default. If enabled later, providers are attempted in configured order and failure falls through to the next provider.

AI recommendations must remain reviewable and must not directly delete, overwrite, or move original source files.
