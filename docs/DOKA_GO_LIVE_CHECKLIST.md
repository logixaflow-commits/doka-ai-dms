# Doka cloud setup and release checklist

Last reviewed: 2026-10-02

## Active production architecture

- Frontend: Vercel — `https://enterprise-ai-dms.vercel.app`
- Cloud API: Cloudflare Python Worker — `https://doka.logixaflow.workers.dev`
- Auth, metadata and object storage: Supabase project `jkobgssaqifzrqfirdfu`
- Private Storage bucket: `doka-documents`, 50 MiB per-object limit
- Local Personal edition: FastAPI/local filesystem/OCR runtime; it is not hosted in the cloud Worker.

Render is not part of the active deployment. The free Render option was not selected because it requires a payment card; do not create a Render service or enable paid billing without an explicit decision.

## Verified current state

- Cloudflare Worker version 87 (`99f174d7-b228-4746-900d-210a6816de53`) is receiving 100% traffic. It includes authenticated document lifecycle, preview, version history, folder listing, atomic bulk status/Trash and audit routes.
- Supabase has 17 applied Doka migrations through `20261002095029_doka_bulk_updated_at_trigger`.
- Owner-scoped RLS and private Storage policies are installed. Version RPCs validate `auth.uid()` and the parent document owner; anonymous users cannot execute version/bulk RPCs.
- Vercel production deployment `dpl_BoY7ur6K8751F77DsGPoRsPvtutS` (commit `7846669f`) is READY and owns the production alias. Its production bundle was checked for version history, preview, folder filtering, atomic bulk actions, Activity and batch upload/retry.
- The current production JavaScript bundle was checked and includes Version history, safe preview, folder filtering, atomic bulk actions, Activity and the sequential batch-upload queue with retry.
- Doka Quality Checks passed on commit `5ad3efa7`; Local Core Checks passed on `0807b5c3`. Follow-up documentation/migration changes have separate Local Core runs.
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
- The Security Advisor still reports the authenticated SECURITY DEFINER version RPCs and leaked-password protection disabled. The version functions explicitly validate the signed-in owner; keep this warning under review and do not broaden execute grants.
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
