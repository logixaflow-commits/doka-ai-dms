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

Separate **authenticated acceptance** still requires two distinct disposable staging-user JWTs (`DOKA_CLOUD_USER_A_TOKEN`, `DOKA_CLOUD_USER_B_TOKEN`) and the exact-50-MiB fixture. The GitHub workflow pins the base URL to the exact staging Worker. Provider recovery also requires staging-only B2, Cloudinary and Google Drive credentials. Never use production user tokens, a production service-role key, or production document data.

## Deployment and verification

1. Push to the dedicated `fix/staging-rpc-security-parity` branch (or dispatch **Cloudflare Worker Staging Deploy** with `confirm_nonproduction=true`).
2. The workflow runs a Python Worker dry-run build before deployment.
3. It deploys only the `doka-ai-dms-staging` Worker and sets a fresh staging-only upload-session secret.
4. It checks `/health`, `/api/config`, preview-origin CORS response headers, and `OPTIONS` preflight. The latest guarded run passed preflight using browser-like request headers; bare automation probes may be blocked by Cloudflare edge error 1010.
5. For authenticated acceptance, configure two distinct disposable staging-user JWTs in `DOKA_CLOUD_USER_A_TOKEN` and `DOKA_CLOUD_USER_B_TOKEN`, then run `scripts/cloud_acceptance.py` with the exact 50-MiB fixture. The GitHub workflow pins the base URL to staging and the runner refuses production.
6. Save scrubbed evidence and only mark the release candidate ready after real A/B isolation, 50 MiB, byte-integrity, lifecycle, provider recovery and OCR tests pass.

## Current status

The staging Worker has been deployed at `https://doka-ai-dms-staging.logixaflow.workers.dev`; `/health`, `/api/config`, preview-origin CORS GET header and OPTIONS preflight checks pass, and the Worker is bound to the staging Supabase project and staging D1. The staging RPC migration also passed transaction-scoped SQL lifecycle/version/restore/bulk-trash/cross-user checks with all temporary fixtures rolled back. The latest guarded staging run passes the GET CORS policy and OPTIONS preflight smoke. A real Preview UI authenticated browser flow is still pending. Authenticated User A/B lifecycle, exact-50-MiB integrity, provider recovery, strict OCR and measured restore RTO/RPO remain pending. Keep release status blocked until those checks have passed.

## Render decision

The current cloud application runtime is the Cloudflare Python Worker. The FastAPI entry point is the Personal Local Edition and must not be exposed as a public Render service. A Render Web Service is not required to deploy the existing cloud API. Revisit Render only if a separately reviewed cloud API adapter is needed; use a Free plan only if the account confirms it remains $0, and keep its configuration isolated from production.
