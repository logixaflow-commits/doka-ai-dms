# Doka Environment Matrix

Last reviewed: 2026-10-05

## Initial operating scope

Doka is initially operated as a single-user deployment. Supabase Auth and owner-scoped RLS remain enabled. Set DOKA_SINGLE_USER_EMAIL to the one approved Google/Supabase account when the remote deployment is ready. Leaving it empty preserves normal authenticated multi-user behavior.

## Vercel

Keep the existing Supabase public variables. Add VITE_SENTRY_DSN when the Sentry frontend project exists. VITE_API_BASE_URL is optional because the frontend defaults to the deployed Cloudflare Worker URL.

Never put service-role keys, Cloudinary API secrets, QStash secrets, or Sentry auth tokens in VITE variables.

Vercel is intentionally paused; do not resume or modify deployment state unless explicitly requested.

## Cloudflare Worker

Required runtime values:
- SUPABASE_URL
- SUPABASE_STORAGE_BUCKET
- DOKA_STORAGE_MAX_OBJECT_BYTES
- SUPABASE_PUBLISHABLE_KEY as a secret binding
- DOKA_SINGLE_USER_EMAIL as an optional allowlist

Do not put Supabase service-role/secret keys in the Worker.

## Render

Render is an alternate FastAPI deployment, not the active Cloudflare API path. If activated, configure:
- PYTHON_VERSION=3.12.8
- ENVIRONMENT=production
- DEBUG=false
- SECRET_KEY generated secret
- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- DOKA_SINGLE_USER_EMAIL optional
- SENTRY_DSN
- DOKA_STORAGE_PROVIDER=supabase
- SUPABASE_STORAGE_BUCKET=doka-documents
- DOKA_STORAGE_MAX_OBJECT_BYTES=52428800
- CORS_ORIGINS with exact frontend origin(s)
- ORIGINAL_READ_ONLY=true
- ALLOW_SOURCE_WRITE=false

## Cloudinary

Server-side only:
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

## Sentry

Frontend uses VITE_SENTRY_DSN. FastAPI uses SENTRY_DSN. Telemetry scrubbing removes request bodies, cookies, URLs, user identity, arbitrary tags/contexts, exception messages, and stack-frame locals/paths.

This repository has no Sentry account-management connector, so creating the actual Sentry project and DSN remains a Sentry dashboard action.

## Not currently required

AI provider keys remain optional and disabled by default. R2 remains disabled unless billing/activation requirements are explicitly accepted. QStash/Redis credentials are not added to unrelated services until the production queue path is enabled and verified.

## Cloud storage routing additions

For the direct-upload Cloud Edition also configure:
- `STORAGE_PROVIDER=hybrid` (or `mock` for local contract testing)
- `DOKA_STORAGE_SESSION_SECRET` (32+ bytes)
- `B2_ENDPOINT`, `B2_BUCKET`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_REGION` when >50 MiB sources are enabled
- `B2_QUOTA_BYTES`, `B2_QUOTA_ALERT_RATIO=0.80`, `B2_QUOTA_BLOCK_RATIO=0.95`
- `B2_QUOTA_ALERT_WEBHOOK` optional for the 80% warning
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_LOW_CREDIT_THRESHOLD=5` for derivative routing
- `VITE_DOKA_MAX_UPLOAD_BYTES` optional frontend hint; the Worker remains authoritative

Google Drive export/backup remains configuration-gated until a real OAuth/provider integration is available. Do not mark Drive fallback as live from environment variables alone.
