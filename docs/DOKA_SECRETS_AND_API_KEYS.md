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
| Python API (once its host is selected) | That host's server-side environment / secret manager | SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, storage provider credentials, AI/OCR provider secrets |
| Supabase Edge Functions (only if a provider call is moved there) | Supabase Dashboard → Edge Functions → Secrets | Only secrets used by those Edge Functions |
| Local development | ignored .env file based on .env.example | local-only test credentials; never commit |

The current Vercel project is the frontend deployment. Do not assume it is also hosting the Python API. The backend host is still a separate architecture decision.

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
- R2_BUCKET
- R2_ENDPOINT_URL
- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY

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
- DOKA_STORAGE_MAX_OBJECT_BYTES=52428800
- DOKA_STORAGE_MAX_TOTAL_BYTES=0

## Important

A key is not automatically usable just because it is stored in Vercel or Supabase. The deployed backend/Edge Function must read that exact variable, and its code must implement the provider adapter. Keep unused keys out until their integration is selected. Do not paste keys into this chat; provide only provider names and (if needed) masked key labels.