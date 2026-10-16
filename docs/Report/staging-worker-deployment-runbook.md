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
- `.github/workflows/cloudflare-worker-staging-deploy.yml`: manually dispatched staging-only deployment, guarded by a required confirmation input and refusing the main branch.

## Required GitHub Actions secrets

Configure these in the repository before running the staging workflow:

- `CLOUDFLARE_API_TOKEN`: token scoped to the correct Cloudflare account and Workers deployment permissions.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.
- `SUPABASE_STAGING_PUBLISHABLE_KEY`: publishable key from the staging Supabase project only.
- `DOKA_STAGING_STORAGE_SESSION_SECRET`: unique random staging-only secret of at least 32 characters.

Do not use the production Supabase secret/service-role key. Do not add any secret to Vite/browser-prefixed variables or commit it to Git. The deployment workflow deliberately fails early if required secrets are missing.

## Deployment and verification

1. Dispatch **Cloudflare Worker Staging Deploy** from this non-main branch and set `confirm_nonproduction=true`.
2. The workflow runs a Python Worker dry-run build before deployment.
3. It deploys only the `doka-ai-dms-staging` Worker, then sets staging-only secrets.
4. It checks `/health` and `/api/config` and requires staging Auth and Storage configuration to be present.
5. After the workflow passes, configure `DOKA_CLOUD_BASE_URL` and two disposable staging-user JWTs as GitHub Actions secrets, then manually dispatch **Authenticated Cloud Acceptance** with `confirm_nonproduction=true`. The acceptance runner refuses the known production Worker host.
6. Save scrubbed evidence and only mark the release candidate ready after user isolation, 50 MiB, byte-integrity, lifecycle, provider recovery and OCR tests pass.

## Current status

The config and guarded workflow are committed to the PR branch, but the staging Worker has **not** been deployed by this commit. Deployment is pending the required repository secrets and a successful dry-run. The existence of staging databases or deployment code is not evidence of live acceptance. Keep release status blocked until live checks have passed.

## Render decision

The current cloud application runtime is the Cloudflare Python Worker. The FastAPI entry point is the Personal Local Edition and must not be exposed as a public Render service. A Render Web Service is not required to deploy the existing cloud API. Revisit Render only if a separately reviewed cloud API adapter is needed; use a Free plan only if the account confirms it remains $0, and keep its configuration isolated from production.
