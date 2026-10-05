# Doka cloud setup and release checklist

Last reviewed: 2026-10-05

## Active production architecture

- Frontend: Vercel — `https://enterprise-ai-dms.vercel.app`
- Cloud API: Cloudflare Python Worker — `https://doka.logixaflow.workers.dev`
- Auth, metadata and object storage: Supabase project `jkobgssaqifzrqfirdfu`
- Private Storage bucket: `doka-documents`, 50 MiB per-object limit
- Local Personal edition: FastAPI/local filesystem/OCR runtime; it is not hosted in the cloud Worker.

Render is not part of the active deployment. The free Render option was not selected because it requires a payment card; do not create a Render service or enable paid billing without an explicit decision.

## Verified current state

- Cloudflare Worker `doka` latest deployment (2026-10-05 07:39 UTC) is receiving 100% traffic on version `2655ae42-b180-432e-b87f-542c97f9e8ce`; the Cloudflare API reports the deployment source as Wrangler.
- Supabase has the Doka schema migrations through `20261005073729_doka_version_rpc_execute_hardening`.
- Owner-scoped RLS and private Storage policies are installed. Version RPCs validate `auth.uid()` and the parent document owner; anonymous users cannot execute version/bulk RPCs.
- Vercel production is intentionally paused by the owner; do not reactivate or deploy it without explicit authorization. Deployment `dpl_vyP8LeS8eNNJcLHKMMqLk8mEPGdr` for commit `280060321c9d0508ae18eabf3859dd11d8988739` is READY and owns `enterprise-ai-dms.vercel.app`. The production HTTP smoke check returned 200 with the expected Doka title.
- The latest Vercel production build succeeded after fixing Tailwind/PostCSS import ordering in `web-platform/frontend/src/index.css`; `npm ci` reported 0 vulnerabilities during the build. Interactive authenticated production acceptance is still pending.
- Doka Quality Checks run 485 on commit `34f961c987404e5b880fe5b37c9252434fe366ec` completed successfully across backend regression, frontend build/smoke, dependency audits, symlink security and CodeQL/SBOM.
- Authenticated upload/restore/version and two-user isolation have not yet been proven with separate real user sessions.

## Vercel frontend configuration

Set the following in Vercel Project → Settings → Environment Variables for the required environments:

- `VITE_SUPABASE_URL=https://jkobgssaqifzrqfirdfu.supabase.co`
- `VITE_SUPABASE_PUBLISHABLE_KEY=<active sb_publishable key from Supabase API Keys>`
- `VITE_API_BASE_URL=https://doka.logixaflow.workers.dev`

Use only the Supabase publishable key in browser variables. Never put a service-role/secret key or AI provider key in any `VITE_*` variable.

### Automated production deployment

The repository includes `.github/workflows/vercel-production.yml`. It runs `vercel pull`, `vercel build --prod` and `vercel deploy --prebuilt --prod` using the configured Vercel project/team IDs.

Required GitHub Actions secret:

- `VERCEL_TOKEN`: a Vercel access token with permission to deploy this project.

The workflow check completed successfully but skipped its CLI deployment because this secret is currently absent. Vercel's connected Git integration has already produced the current READY production deployment. The `VERCEL_TOKEN` secret is required only if you want the repository's explicit CLI deploy workflow as a fallback; after adding it, open GitHub → Actions → Vercel Production Deploy → Run workflow.

## Cloudflare Worker configuration

Root `wrangler.jsonc` defines:

- `SUPABASE_URL=https://jkobgssaqifzrqfirdfu.supabase.co`
- `SUPABASE_STORAGE_BUCKET=doka-documents`
- `DOKA_STORAGE_MAX_OBJECT_BYTES=52428800`

The Worker also requires the secret `SUPABASE_PUBLISHABLE_KEY`, stored as a Cloudflare secret binding. Do not configure a service-role key. The active build trigger uses `uv run pywrangler deploy` from repository root.

Verify after future Worker deployments:

- `GET /health` returns healthy.
- `GET /api/config` reports Supabase Auth and Storage configured.
- Unauthenticated or invalid-token document/version/bulk routes return 401.
- New Worker version receives 100% traffic.

## Supabase security and schema

- Keep `doka-documents` private.
- Preserve owner-scoped RLS for documents, audit events and versions.
- Storage object keys must remain under `users/{auth.uid()}/...`.
- Only trashed documents can be permanently deleted.
- Version replacement/restore RPCs must retain explicit owner and object-path validation.
- Bulk RPC remains SECURITY INVOKER and relies on existing column-level grants and RLS.
- Supabase Security Advisor now reports only leaked-password protection disabled. The version-RPC SECURITY DEFINER finding was cleared after revoking direct `authenticated` execution; the repository now carries the same hardening as a migration.
- Recheck Security and Performance Advisors after schema changes. Do not remove unused indexes until representative workload evidence exists.

## Required acceptance before real use

- Confirm Vercel public environment variables and the Worker API origin.
- Confirm Worker health/config and the latest Worker deployment version.
- With a real signed-in user, test upload, list/search/folder filter, rename/move, status update, preview, download, version create/restore, Trash/restore, permanent delete, Activity and atomic bulk operations.
- Verify a second user cannot read, modify, preview, download, restore or delete the first user's documents or objects.
- Test the 50 MiB boundary and confirm 413 behavior above the configured limit.
- Check batch upload queue success/failure/retry in the production browser after deploying the latest frontend.
- Run desktop/mobile visual and keyboard acceptance on authenticated pages; login-only layout checks do not prove dashboard/sidebar behavior.
- Run the Personal Local pilot only against a separate copy of representative office data. Use `scripts/doka_pilot_check.py` and `scripts/ocr_benchmark.py`; never point these tools at original source folders.
- Record Myanmar/English OCR CER/WER and manually review low-scoring samples. See `docs/DOKA_OCR_BENCHMARK.md`.
- Review the npm/Dependabot advisory set before release. Do not claim alerts are resolved until each alert is verified against the locked dependency tree and CI.

## AI and external providers

- Keep `AI_ENABLED=false` until the production consent UX, provider adapters, data redaction, quotas and audit behavior are implemented and tested.
- External processing must require explicit user consent in addition to the global AI enable flag.
- Never upload confidential documents to an external provider solely because a key is configured.
- Store provider keys only in the server-side environment of the service that makes the call.

## Free-service policy

Use only the services currently needed:

- GitHub: source control, CI and Dependabot.
- Vercel: frontend.
- Cloudflare Workers: stateless cloud API.
- Supabase: Auth, Postgres metadata and private Storage.
- Cloudflare R2: optional only if Storage limits justify a second object store.
- Sentry: optional privacy-scrubbed error telemetry.

Do not add another database, Redis, another frontend host, a separate vector database or email service until a concrete feature requires it. Do not enable paid plans or billing without explicit approval.
