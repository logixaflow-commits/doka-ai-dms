# Doka FastAPI Cloud API deployment

## Deployment boundary

The Personal Local Edition continues to run from `app.main:app` and retains its local workspace, filesystem import, OCR, backup, and recovery routes.

The stateless cloud service runs from `app.cloud_main:app`. It mounts only:
- `/health`
- `/api/config`
- `/api/documents`
- `/api/storage`

It deliberately does **not** mount `/api/workspace` or local password authentication. A free cloud web service has an ephemeral filesystem and must never be treated as the user's durable office workspace. Cloud document bytes and metadata remain in the private Supabase Storage bucket and owner-scoped Postgres tables.

## Render Web Service

Use the repository `logixaflow-commits/enterprise-ai-dms`, branch `main`, and repository root as the service root.

- Runtime: Python
- Region: Singapore (or nearest available region)
- Plan: Free for a no-cost pilot only
- Build command: `pip install -r web-platform/backend/requirements-cloud.txt`
- Start command: `cd web-platform/backend && uvicorn app.cloud_main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

Free instances can spin down when idle and have ephemeral filesystems. Cold starts are expected. Do not store user documents, SQLite databases, workspace imports, or backups on this service. Use Supabase for durable cloud data. Local OCR and filesystem workflows continue to run on the user's own machine.

## Required service environment

Set these in the API host's server-side environment; never put a service-role key in the browser:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `SECRET_KEY=<unique random server-only secret, at least 32 random bytes>`
- `SUPABASE_URL=https://<project-ref>.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY=<current sb_publishable key>`
- `DOKA_STORAGE_PROVIDER=supabase`
- `SUPABASE_STORAGE_BUCKET=doka-documents`
- `DOKA_STORAGE_MAX_OBJECT_BYTES=52428800`
- `CORS_ORIGINS=https://enterprise-ai-dms.vercel.app`
- `ORIGINAL_READ_ONLY=true`
- `ALLOW_SOURCE_WRITE=false`

Add exact Vercel Preview origins to `CORS_ORIGINS` only if Preview deployments need API access. Do not use `*` for authenticated endpoints.

## Vercel frontend

Set this Vite build-time variable in Vercel for Production (and Preview if required):

- `VITE_API_BASE_URL=https://<actual-api-service-host>`

The frontend appends `/api` and forwards the signed-in user's Supabase access token. The local Vite development proxy remains unchanged and forwards `/api` to `http://localhost:8000`; leave `VITE_API_BASE_URL` unset for local development.

After changing the Vercel variable, redeploy the frontend. Do not set `VITE_API_BASE_URL=/api` when using a separate API host.

## Verification before real use

1. Confirm API `/health` returns JSON with `status=healthy` and `edition=cloud-api`.
2. Confirm `/api/config` returns `edition=cloud-api`, `auth=supabase`, and `local_workspace_available=false`.
3. Confirm `/api/workspace/imports` is not mounted (404).
4. Confirm unauthenticated `/api/documents` returns 401.
5. Sign in with a test Supabase user and test list, upload, metadata update, and signed download.
6. Verify a second test user cannot list, read, update, or download the first user's records or objects.
7. Confirm uploads over 50 MiB are rejected.
8. Only after all checks pass should the cloud document UI be used with real data.

Never claim the cloud API is production-ready based only on a successful deploy or health check. Authenticated data-flow and cross-user isolation tests are required.
