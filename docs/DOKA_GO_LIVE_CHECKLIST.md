# Doka cloud setup and release checklist

Last reviewed: 2026-10-02

## Already completed

- GitHub main branch is the source of truth; no feature branch workflow is used.
- Vercel project `enterprise-ai-dms` exists and has produced READY production deployments. It hosts the Vite frontend only. The latest observed READY production deployment still points to commit `f2b2c75`; newer main commits have not yet appeared in the deployment list, so production is not confirmed to contain the latest code.
- Supabase project `jkobgssaqifzrqfirdfu` is active in `ap-southeast-1`.
- Four Doka SQL migrations are applied to the live Supabase project, and their repository filenames are aligned with the applied migration versions.
- `public.doka_documents` and `public.doka_document_versions` exist with RLS enabled.
- Private `doka-documents` Storage bucket exists with a 50 MiB object limit.
- Owner-scoped Storage policies and table policies are installed.
- Authenticated document updates are column-restricted to `status` and `metadata`.
- Supabase-generated TypeScript database types are committed at `web-platform/frontend/src/types/database.types.ts`.
- Dependabot weekly update checks are configured for frontend npm, backend pip, and GitHub Actions dependencies.
- AI remains disabled by default.

## Remaining deployment configuration

### Vercel frontend

Set these public browser configuration values in Vercel Project → Settings → Environment Variables for Production, Preview, and Development as appropriate:

- `VITE_SUPABASE_URL=https://jkobgssaqifzrqfirdfu.supabase.co`
- `VITE_SUPABASE_PUBLISHABLE_KEY=<active sb_publishable key from Supabase API Keys>`

Do not put service-role/secret keys or AI provider keys in Vercel `VITE_*` variables.

Set `VITE_API_BASE_URL` to the FastAPI Cloud API origin (for example, `https://doka-cloud-api.onrender.com`) after the Render service has been created and its actual URL is confirmed. Do not append `/api` or use `/api` as the production value. The frontend adds `/api` itself. Leave it unset for local development so Vite continues proxying to `http://localhost:8000`.

The connected Vercel tools currently do not expose project environment-variable read/write operations, so those Vercel values have not been changed or verified from this workflow.

### FastAPI Cloud API host (Render blueprint prepared; service not yet created)

A root-level `render.yaml` now defines a free Singapore Render Web Service running `app.cloud_main:app`. This is a stateless cloud API for Supabase-backed Cloud Documents only; it does not provide the Personal Local filesystem, OCR, workspace import, backup, or recovery runtime. Render Free can spin down when idle and has an ephemeral filesystem. It is not a durable office-file data plane and is not a remote OCR host.

The Blueprint generates a server-only `SECRET_KEY` and prompts for the Supabase project URL and publishable key. Configure these server-side values:

- `ENVIRONMENT=production`
- `SUPABASE_URL=https://jkobgssaqifzrqfirdfu.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY=<active sb_publishable key>`
- `DOKA_STORAGE_PROVIDER=supabase`
- `SUPABASE_STORAGE_BUCKET=doka-documents`
- `DOKA_STORAGE_MAX_OBJECT_BYTES=52428800`
- `CORS_ORIGINS=<exact Vercel production and preview origins>`
- `SECRET_KEY=<strong randomly generated server-only value>`

Keep local password login disabled in production. Do not use the Supabase service-role key for ordinary per-user document operations.

The Render workspace must be explicitly confirmed before creating the service. Do not enable a paid plan or provide billing details. Remote OCR is still intentionally unhosted; it remains a local-machine capability until a separately measured and funded runtime is chosen.

### Optional Cloudflare R2

Do not configure R2 until the Supabase Storage allowance is insufficient or a second object-store target is explicitly needed. The adapter is in the code, but no R2 account credentials have been configured.

If selected later, configure server-side only:

- `DOKA_STORAGE_PROVIDER=r2`
- `R2_BUCKET`
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

R2 usage is free only within its published monthly allowance; usage beyond it can be billed. Keep usage monitoring and a quota cap enabled before uploading real office files.

## AI and external provider keys

- Existing code paths documented as supported: Gemini, OpenRouter, Groq, OpenAI, and Hugging Face.
- Planned, not yet integrated: NVIDIA Build (exact API/product must be confirmed), Cerebras, Mistral, Cohere, Voyage AI.
- Canva is a separate OAuth/design integration, not an LLM provider.
- Cloudflare R2 credentials do not enable Workers AI.
- Keep `AI_ENABLED=false` until provider adapters, privacy consent, limits, and tests are complete.
- Do not upload confidential documents to an external AI provider simply because an API key is configured.

Store keys only in the server-side environment of the service that calls them. Never commit them or put them in browser variables.

## Required validation before real use

- Confirm Vercel frontend has the two Supabase public values and set `VITE_API_BASE_URL` to the actual Render API origin after service creation.
- Create the Render service from `render.yaml`; configure the Supabase URL and publishable key as server-side variables and confirm `/health`.
- Run authenticated upload, list, metadata update, and signed download tests with a real Supabase user.
- Verify SHA-256 values and confirm a different user cannot read, modify, or download the first user's records or objects.
- Test 413 behavior at the 50 MiB object limit.
- Run the Phase D pilot only against a separate copy of representative office data; never use the original source folder.
- Confirm the latest GitHub Actions workflow run is green and trigger/verify a Vercel production deployment from the current main commit before browser E2E.
- Run browser E2E after code and cloud configuration are stable.
- Keep the leaked-password-protection advisor warning acknowledged as a Free-plan limitation per project decision; do not treat it as an unresolved code migration.

## Free-service policy

Use only what the product currently needs:

- GitHub: source control, CI, Dependabot.
- Vercel: frontend.
- Supabase: Auth, Postgres metadata, private Storage.
- Cloudflare R2: optional larger object storage.
- Sentry: optional privacy-scrubbed error telemetry.

Do not add a second database, Redis, another frontend host, a separate vector database, or email service until a concrete feature requires it. Avoid any paid plan or billing enablement for the free-only baseline.
