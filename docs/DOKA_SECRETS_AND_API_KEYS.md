# Doka secrets and API-key placement

## Rules
- Never commit real keys, passwords, access tokens, service-role keys, or .env files.
- Never put provider secrets in VITE_ variables: Vite exposes those values to every browser user.
- The Supabase publishable key is intentionally public and may use the VITE_ prefix. The Supabase service-role/secret key is server-only and is not required by the current user-scoped Storage/Data API design.
- Store each secret in the environment of the service that actually calls that provider. Do not duplicate keys into the database or frontend bundle.
- Use separate Development / Preview / Production values where the provider supports it. Rotate any key that was ever committed or pasted into source code.

## Current application split

| Service | Store here | What belongs here |
|---|---|---|
| Doka web frontend | Vercel Project → Settings → Environment Variables | VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY, VITE_API_BASE_URL only |
| Python API (once its host is selected) | That host's server-side environment / secret manager | SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, CORS_ORIGINS, storage provider credentials, AI/OCR provider secrets |
| Supabase Edge Functions (only if a provider call is moved there) | Supabase Dashboard → Edge Functions → Secrets | Only secrets used by those Edge Functions |
| Local development | ignored .env file based on .env.example | local-only test credentials; never commit |

The current Vercel project is the frontend deployment. Do not assume it is also hosting the Python API. The backend host is still a separate architecture decision. Vercel's current catch-all rewrite serves the Vite SPA; it is not a Python API proxy. Until a backend host and route are configured, leave VITE_API_BASE_URL unset in production rather than assuming /api reaches FastAPI.

## Supabase values for this project

Project ref: jkobgssaqifzrqfirdfu

- Project URL: https://jkobgssaqifzrqfirdfu.supabase.co
- Publishable key: retrieve the active sb_publishable_... key from Supabase → Project Settings → API Keys. It is public by design.
- Do not use the legacy service_role key in the frontend.
- Do not add a Supabase service-role key to Doka for ordinary per-user document operations. The current API uses the signed-in user's bearer token and RLS.

## Provider key names reserved for Doka

Add only keys for providers that are actually selected and used:

- GEMINI_API_KEY (already supported by the local AI fallback)
- OPENROUTER_API_KEY (already supported)
- GROQ_API_KEY (already supported)
- OPENAI_API_KEY (already supported)
- HUGGINGFACE_API_KEY (already supported)
- ANTHROPIC_API_KEY (reserved; adapter not yet confirmed)
- GOOGLE_API_KEY (reserved alternate Gemini name; current code uses GEMINI_API_KEY)
- MISTRAL_API_KEY (reserved; adapter not yet confirmed)
- AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
- AZURE_DOCUMENT_INTELLIGENCE_KEY
- GOOGLE_CLOUD_PROJECT
- GOOGLE_APPLICATION_CREDENTIALS_JSON (server-side JSON secret only; never a file committed to Git)
- CLOUDFLARE_ACCOUNT_ID
- CLOUDFLARE_API_TOKEN

Existing AI settings in backend .env.example:
- AI_ENABLED=false (AI stays off until deliberately enabled)
- AI_PROVIDER_ORDER=gemini,openrouter,groq,openai
- AI_PROVIDER_MAX_ATTEMPTS=0
- AI_PROVIDER_TIMEOUT_SECONDS=30
- GEMINI_MODEL=gemini-2.5-flash-lite
- OPENROUTER_MODEL=openrouter/free
- GROQ_MODEL=openai/gpt-oss-20b
- OPENAI_MODEL=gpt-4o-mini
- HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2

Existing optional Doka controls:
- DOKA_STORAGE_PROVIDER=disabled|supabase|r2
- SUPABASE_STORAGE_BUCKET=doka-documents
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET
- DOKA_STORAGE_MAX_OBJECT_BYTES=52428800
- DOKA_STORAGE_MAX_TOTAL_BYTES=0

## Important

A key is not automatically usable just because it is stored in Vercel or Supabase. The deployed backend/Edge Function must read that exact variable, and its code must implement the provider adapter. Keep unused keys out until their integration is selected. Do not paste keys into this chat; provide only provider names and (if needed) masked key labels.

## User-provided provider and service inventory (2026-10-01)

The following services are in the planned integration inventory. Possessing an API key does not mean Doka has an adapter for it yet.

| Service | Intended Doka role | Current code status | Secret / credential handling |
|---|---|---|---|
| Gemini | General-purpose LLM / document assistance | Existing adapter documented as supported | `GEMINI_API_KEY` |
| OpenRouter | Multi-model LLM gateway and fallback | Existing adapter documented as supported | `OPENROUTER_API_KEY` |
| Hugging Face | Embeddings / inference | Existing adapter documented as supported; validate the selected task/model before production use | `HUGGINGFACE_API_KEY` |
| NVIDIA Build / NVIDIA API | Hosted model inference (exact product/API endpoint to confirm) | Not yet integrated | Candidate: `NVIDIA_API_KEY`; endpoint/model configuration must be confirmed |
| Cerebras | Fast hosted LLM inference | Not yet integrated | Candidate: `CEREBRAS_API_KEY` |
| Mistral | LLM and document understanding | Not yet integrated | `MISTRAL_API_KEY` is reserved |
| Cohere | Embeddings, reranking, and language models | Not yet integrated | Candidate: `COHERE_API_KEY` |
| Groq | Hosted LLM inference | Existing adapter documented as supported | `GROQ_API_KEY` |
| Canva | Design/export integration, not a general-purpose LLM provider | Not yet integrated; OAuth/app setup may be required rather than a simple API key | Do not add a secret until the Canva app/OAuth flow is designed |
| Voyage AI | Embeddings and reranking | Not yet integrated | Candidate: `VOYAGE_API_KEY` |
| Cloudflare | Object storage via R2; potential edge/AI services | R2 adapter is implemented; Workers AI and other Cloudflare services are not thereby enabled | R2: `R2_BUCKET`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`; account/token variables only for a feature that needs them |

### Integration and privacy rules

- Keep the current local/rule-based workflow usable without any external AI provider.
- Keep `AI_ENABLED=false` by default. Enabling AI must be an explicit operator choice.
- Do not send document contents to a provider merely because its key is configured. Each document-processing feature must explicitly opt in, disclose the destination/provider, and use only the minimum required content.
- Embedding and reranking providers (for example Voyage AI or Cohere) must be configured as separate capabilities; do not treat them as interchangeable chat-completion providers.
- Canva must be handled as a separate OAuth/product integration, not inserted into the LLM provider fallback chain.
- Cloudflare R2 object storage credentials are separate from Cloudflare Workers AI credentials. Implementing one does not enable the other.
- Before adding any new key to `.env.example`, implement and test the corresponding adapter and document its exact supported endpoint, model/task, timeout, and failure behavior.
- The exact NVIDIA product meant by “NVIDIA Build” must be confirmed before implementation so Doka uses the correct API base URL and authentication scheme.


## Verified production environment configuration (2026-10-01)

The live Supabase project is active at `https://jkobgssaqifzrqfirdfu.supabase.co`. The current production Vite bundle was verified to contain:
- `VITE_SUPABASE_URL` for this project.
- `VITE_SUPABASE_PUBLISHABLE_KEY` using an active `sb_publishable_` key. This is public by design; do not treat it as a server secret.

The Vercel production build therefore had the two required browser-safe Supabase values at build time. The connected Vercel tools available in this session do not expose an environment-variable inventory or mutation operation, so the dashboard's full Production/Preview/Development variable list could not be inspected or edited directly. If these values are rotated, set both in Vercel Project → Settings → Environment Variables, scoped to Production and Preview as required, then redeploy.

`VITE_API_BASE_URL` is intentionally not set: the Python API host and HTTPS proxy route have not been selected. Do not point it at `/api`; Vercel currently rewrites unknown paths to the SPA. Do not add AI-provider keys, R2 credentials, `SUPABASE_SERVICE_ROLE_KEY`, or any other server-only secret to Vercel's Vite `VITE_` environment.

Supabase live authorization was also tightened on 2026-10-01. Migration `20261001100118_doka_least_privilege_grants` revokes all Doka table privileges from `anon`/PUBLIC and grants only the operations used by the app to `authenticated`; owner-scoped RLS remains the row-level boundary. Migration `20261001100500_doka_storage_no_overwrite_policy` removes the Doka Storage object-update policy because all Doka uploads use `x-upsert=false`. Live grants and policies were queried after applying both migrations.
