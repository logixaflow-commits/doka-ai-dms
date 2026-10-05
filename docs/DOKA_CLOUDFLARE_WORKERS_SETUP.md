# Doka Cloudflare Workers deployment

This repository contains a dedicated Cloudflare Python Worker entry point at
`cloudflare_worker/main.py`. It exposes only the stateless Supabase-backed Cloud
Documents API. The Personal Local Edition, local filesystem, OCR, and backup
features remain on the user's own computer.

## Current deployment

The Cloudflare Worker is deployed as:

- Worker: `doka-ai-dms`
- URL: `https://doka-ai-dms.logixaflow.workers.dev`
- `GET /health`: verified HTTP 200 with `status: healthy`.
- `GET /api/config`: verified HTTP 200 with `edition: cloud-api`,
  `auth: supabase`, `local_workspace_available: false`,
  `supabase_auth_configured: true`, and `storage_bucket_configured: true`.
- Unauthenticated/invalid-token document API requests return HTTP 401, not a
  configuration error.

## Cloudflare Workers Builds setup

The repository root contains `wrangler.jsonc` and `pyproject.toml`, so use
the repository root as the Root directory.

The live Workers Build trigger is configured as:

- **Root directory:** `/`
- **Build command:** blank
- **Deploy command:** `uv run pywrangler deploy`
- **Branch:** `main`

The Build command must remain blank. Pywrangler runs as the Deploy command so
that it prepares and bundles the Python dependencies before Wrangler deploys.

On the Cloudflare "Set up your application" screen:

- **Build command:** Leave blank.
- **Enable Preview builds:** Off for the initial production setup.
- **Protect with Cloudflare Access:** Off. The API authenticates each request
  with the user's Supabase access token; Access would add a second interactive
  login in front of the API.
- **Advanced settings:** Keep the Root directory at `/` (repository root).

The Wrangler configuration uses the existing Worker name `doka-ai-dms`, points to
`cloudflare_worker/main.py`, enables Python Workers, and keeps dashboard
secrets during deploys.

## Required Worker variables

Non-secret runtime values are declared in the root `wrangler.jsonc` so that
every GitHub-triggered deployment keeps them configured:

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | `https://jkobgssaqifzrqfirdfu.supabase.co` |
| `SUPABASE_STORAGE_BUCKET` | `doka-documents` |
| `DOKA_STORAGE_MAX_OBJECT_BYTES` | `52428800` |

The `SUPABASE_PUBLISHABLE_KEY` is stored as a Cloudflare `secret_text`
binding. It is a browser-safe Supabase publishable key, not a service-role
credential. Never configure a Supabase service-role/secret key in this Worker.

CORS is restricted in the Worker code to
`https://enterprise-ai-dms.vercel.app`.

## Vercel frontend

The production frontend defaults to
`https://doka-ai-dms.logixaflow.workers.dev`. Local Vite development continues to
use the local API proxy. `VITE_API_BASE_URL` is optional and can override the
production API origin (no trailing slash and no `/api` suffix). Vercel production is intentionally paused by the owner; do not reactivate or deploy it without explicit authorization.

## Supabase schema and permissions

The `doka_documents` and `doka_document_versions` tables have RLS enabled.
Owner policies restrict rows to the authenticated user's `auth.uid()`.
The Storage bucket `doka-documents` is private and its policies restrict
objects to the user's `users/{auth.uid()}/...` prefix.

The frontend status/metadata editor requires column-level UPDATE permission on
`doka_documents.status` and `doka_documents.metadata`. This is tracked by
migration `20261002064722_grant_doka_document_status_updates.sql`; the owner
UPDATE policy remains the row-level boundary.

## Verification

- `GET /health`: HTTP 200.
- `GET /api/config`: HTTP 200; Supabase Auth and Storage bindings report ready.
- Invalid bearer token on `GET /api/documents`: HTTP 401.
- Browser-origin requests from the production Vercel site can reach the Worker;
  the API's CORS middleware responds to the production origin.
- GitHub Local Core Checks and Doka Quality Checks passed for the frontend
  redesign commits.

A real signed-in account is still required for end-to-end verification of
document listing, upload, status update, and signed download. Test with a
second account to confirm it cannot access the first account's documents.
Do not create fake user files in production as a substitute for this test.

## Runtime boundary

Cloudflare Python Workers execute Python through Pyodide and support FastAPI
through the Workers ASGI adapter. They are not a general-purpose Uvicorn host.
This Worker uses the Workers Fetch API for outbound Supabase requests and
keeps cloud objects and metadata in Supabase. It does not depend on a persistent
Worker filesystem.

## Free-plan performance caution

Cloudflare Workers Free has CPU and request limits. Waiting for Supabase network
fetches does not count toward CPU time, but Python/Pyodide startup, multipart
parsing, and SHA-256 processing do. Verify authenticated listing and small
uploads before relying on large document uploads. Do not upgrade to a paid plan
without the user's explicit approval.
