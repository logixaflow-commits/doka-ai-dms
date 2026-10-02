# Doka Cloudflare Workers deployment

This repository contains a dedicated Cloudflare Python Worker entry point at
`cloudflare_worker/main.py`. It exposes only the stateless Supabase-backed Cloud
Documents API. The Personal Local Edition, local filesystem, OCR, and backup
features remain on the user's own computer.

## Current deployment

The Cloudflare Worker is deployed as:

- Worker: `doka`
- URL: `https://doka.logixaflow.workers.dev`
- `GET /health`: verified HTTP 200 with `status: healthy`.
- `GET /api/config`: verified HTTP 200 with `edition: cloud-api`,
  `auth: supabase`, and `local_workspace_available: false`.

The Worker currently has these runtime bindings configured in Cloudflare:
`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_STORAGE_BUCKET`,
and `DOKA_STORAGE_MAX_OBJECT_BYTES`. The publishable key is browser-safe;
never configure a Supabase service-role/secret key in this Worker.

## Cloudflare Workers Builds setup

The repository root contains `wrangler.jsonc` and `pyproject.toml`, so use
the repository root as the Root directory.

On the Cloudflare "Set up your application" screen:

- **Build command:** Leave blank (no separate compile step is needed).
- **Enable Preview builds:** Off for the initial production setup.
- **Protect with Cloudflare Access:** Off. The API authenticates each request
  with the user's Supabase access token; Access would add a second interactive
  login in front of the API.
- **Advanced settings:** Keep the Root directory at `/` (repository root).
  Leave the default build environment and compatibility settings unchanged.

The Wrangler configuration uses the existing Worker name `doka`, points to
`cloudflare_worker/main.py`, and enables Python Workers.

## Workers Builds deploy command

In the Worker's **Settings → Builds**, set **Deploy command** to
`uv run pywrangler deploy`. This is important: Cloudflare Workers Builds
defaults to `npx wrangler deploy`, which does not prepare and bundle Python
dependencies through Pywrangler. Keep the Build command blank.

## Required Worker variables

The current Worker already has the following bindings configured. If recreating
the Worker, restore these values in **Settings → Variables and Secrets**:

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | `https://jkobgssaqifzrqfirdfu.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | The project's `sb_publishable_...` key (never the service-role key) |
| `SUPABASE_STORAGE_BUCKET` | `doka-documents` |
| `DOKA_STORAGE_MAX_OBJECT_BYTES` | `52428800` |

The first two may be configured as encrypted secrets; the publishable key is
not a service-role credential. Do not add a Supabase service-role key.
CORS is restricted in the Worker code to
`https://enterprise-ai-dms.vercel.app`.

## Vercel frontend

The production frontend now defaults to
`https://doka.logixaflow.workers.dev`. Local Vite development continues to
use the local API proxy. `VITE_API_BASE_URL` is optional and can override the
production API origin (no trailing slash and no `/api` suffix). A new Vercel
deployment is triggered automatically when the GitHub `main` branch changes.

## Verification

- Open `https://doka.logixaflow.workers.dev/health` and confirm
  `status: healthy` and `edition: cloudflare-workers`.
- Open `/api/config` and confirm `edition: cloud-api`,
  `auth: supabase`, and `local_workspace_available: false`.
- Sign in to the frontend and test document list, upload, metadata update,
  and signed download with a real Supabase test account.
- Test a second account and confirm it cannot list, download, or update the
  first account's documents.

## Runtime boundary

Cloudflare Python Workers execute Python through Pyodide and support FastAPI
through the Workers ASGI adapter. They are not a general-purpose Uvicorn host.
This Worker uses the Workers Fetch API for outbound Supabase requests and
keeps cloud objects and metadata in Supabase. It does not depend on a persistent
Worker filesystem.

## Free-plan performance caution

Cloudflare Workers Free currently allows 10 ms CPU time per HTTP request and
100,000 requests per day. Waiting for Supabase network fetches does not count
toward CPU time, but Python/Pyodide startup, multipart parsing, and SHA-256
processing do. Treat the first deployment as a compatibility and smoke-test
stage: verify health, authenticated document listing, and then small uploads
before relying on large document uploads. Do not upgrade to a paid plan without
the user's explicit approval.
