# Staging Worker Deployment Runbook

Date: 2026-10-16

## Safety boundary

- Staging Worker name: `doka-ai-dms-staging`.
- Staging Supabase project: `gzxybtqquzycogaowdbj`.
- Staging D1 database: `11baa497-e6f7-4054-8e9f-3a21baec93f3`.
- Staging upload limit: 52,428,800 bytes (50 MiB).
- The staging config intentionally does not reference production Supabase or production D1 IDs.
- Never run acceptance against `https://doka-ai-dms.logixaflow.workers.dev`.
- No production deployment workflow or production configuration was modified by this change.

## Deployment files

- `wrangler.staging.jsonc`: isolated staging bindings and staging CORS origin.
- `.github/workflows/cloudflare-worker-staging-deploy.yml`: manually dispatched with explicit confirmation, and auto-deployed only when the dedicated `fix/staging-rpc-security-parity` branch is pushed; the production branch cannot trigger this staging workflow.

## Required GitHub Actions secrets

The staging deploy workflow requires only:

- `CLOUDFLARE_API_TOKEN`: token scoped to the correct Cloudflare account and Workers deployment permissions.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.

The staging Supabase publishable key is a public client key (not a service-role secret) and is configured only in `wrangler.staging.jsonc`. The workflow generates a fresh random `DOKA_STORAGE_SESSION_SECRET` inside the GitHub runner for the staging Worker; it is never printed or committed. This rotates only in-flight signed upload sessions on each staging deploy.

Separate **authenticated acceptance** requires two disposable staging Supabase users and these GitHub Actions secrets: `SUPABASE_STAGING_PUBLISHABLE_KEY`, `DOKA_STAGING_USER_A_EMAIL`, `DOKA_STAGING_USER_A_PASSWORD`, `DOKA_STAGING_USER_B_EMAIL`, and `DOKA_STAGING_USER_B_PASSWORD`. The workflow logs in to the exact staging Supabase project at run time, masks fresh short-lived JWTs, and pins the API base URL to the exact staging Worker. Do not store expiring JWTs as long-lived secrets. Provider recovery additionally requires staging-only Worker bindings for B2 (`B2_ENDPOINT`, `B2_BUCKET`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_REGION`, `B2_QUOTA_BYTES`), Cloudinary (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, optional `CLOUDINARY_LOW_CREDIT_THRESHOLD`), and Google Drive (`GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_REFRESH_TOKEN`, `GOOGLE_DRIVE_FOLDER_ID`). For the optional live Cloudinary test, also add the same staging-only values to Actions secrets `CLOUDINARY_STAGING_CLOUD_NAME`, `CLOUDINARY_STAGING_API_KEY`, and `CLOUDINARY_STAGING_API_SECRET`; these are used only to delete the disposable test asset after the Worker verifies read-back integrity. The `Staging Cloud Provider Acceptance` workflow has a `test_cloudinary` opt-in for this path. Never copy production provider credentials into staging or use production document data.

## Deployment and verification

The local cloud-isolation and provider-acceptance runners must target exactly `https://doka-ai-dms-staging.logixaflow.workers.dev`; they refuse production and arbitrary other hosts before prompting for tokens or sending requests. The provider runner defaults to this staging URL. Do not override it with the production Worker or a Vercel alias.

1. Push to the dedicated `fix/staging-rpc-security-parity` branch (or dispatch **Cloudflare Worker Staging Deploy** with `confirm_nonproduction=true`).
2. The workflow runs a Python Worker dry-run build before deployment.
3. It deploys only the `doka-ai-dms-staging` Worker and sets a fresh staging-only upload-session secret.
4. It checks `/health`, `/api/config`, preview-origin CORS response headers, and `OPTIONS` preflight. The latest guarded run passed preflight using browser-like request headers; bare automation probes may be blocked by Cloudflare edge error 1010.
5. In GitHub Actions, run **Authenticated Cloud Acceptance** with `confirm_nonproduction=true` and the required provider selection. It mints fresh staging User A/B JWTs, exercises lifecycle/isolation, and uploads/downloads an exact 50 MiB fixture. The runner refuses every host except the exact staging Worker.
6. Run **Staging Cloud Provider Acceptance** with `confirm_nonproduction=true` after staging-only B2/Google Drive credentials are configured. It tests B2 (>50 MiB), Supabase version transition, download integrity, Google Drive export, trash/restore, audit events and cleanup.
7. Save scrubbed evidence and only mark the release candidate ready after real A/B isolation, 50 MiB, byte-integrity, lifecycle, provider recovery and OCR tests pass.

## Current status

The staging Worker has been deployed at `https://doka-ai-dms-staging.logixaflow.workers.dev`; `/health`, `/api/config`, preview-origin CORS GET header and OPTIONS preflight checks pass, and the Worker is bound to the staging Supabase project and staging D1. The staging RPC migration also passed transaction-scoped SQL lifecycle/version/restore/bulk-trash/cross-user checks with all temporary fixtures rolled back. The latest guarded staging run passes the GET CORS policy and OPTIONS preflight smoke. A real Preview UI authenticated browser flow is still pending. Authenticated User A/B lifecycle, exact-50-MiB integrity, provider recovery, strict OCR and measured restore RTO/RPO remain pending. Keep release status blocked until those checks have passed.

## Render decision

The current cloud application runtime is the Cloudflare Python Worker. The FastAPI entry point is the Personal Local Edition and must not be exposed as a public Render service. A Render Web Service is not required to deploy the existing cloud API. Revisit Render only if a separately reviewed cloud API adapter is needed; use a Free plan only if the account confirms it remains $0, and keep its configuration isolated from production.
