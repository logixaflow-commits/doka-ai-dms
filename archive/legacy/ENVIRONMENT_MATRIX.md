# Doka Environment Matrix

Last audited: 2026-10-07

This file records **which environment owns which configuration**. It intentionally records names and status, not secret values.

## Service status

| Service | Live state | Role | Current finding |
|---|---|---|---|
| Personal Local | Local-only | FastAPI + React/Vite + filesystem + SQLite + Tesseract | Real-machine evidence still pending |
| Cloudflare Worker | Active | Cloud API | Worker `doka-ai-dms` exists; latest deployment version is 100% traffic; secret bindings present |
| Supabase | Active/healthy | Auth + Postgres/RLS + Storage transition | Leaked-password protection still disabled |
| Vercel | Paused | Frontend hosting target | Project exists; live=false; latest production deployment is CANCELED; owner pause must remain |
| Render | Workspace exists; inspection pending | Deferred/optional cloud FastAPI | Workspace selection requires owner confirmation |
| Cloudinary | Configured as a target, not proven | Private object/derivative storage | Real provider + recovery drill pending |
| Backblaze B2 | Worker secret bindings present | >50 MiB cloud object path | Real upload/recovery drill pending |
| Google Drive | Worker secret bindings present | User-owned export/backup | OAuth/export/recovery drill pending |

## Vercel

Project: `enterprise-ai-dms`

Current environment variables visible to the project manager:

- `DOKA_STORAGE_PROVIDER` — development/preview/production, secret, value not inspected.
- `SUPABASE_STORAGE_BUCKET` — development/preview/production, secret, value not inspected.
- `VITE_SUPABASE_URL` — development/preview/production, browser-visible configuration.
- `VITE_SUPABASE_PUBLISHABLE_KEY` — development/preview/production, browser-safe publishable key.

**Important:** no AI provider key is present in the Vercel environment inventory returned by the project manager.

## Cloudflare Worker

Worker: `doka-ai-dms`

Secret bindings currently present:

- B2: `B2_APPLICATION_KEY`, `B2_BUCKET`, `B2_ENDPOINT`, `B2_KEY_ID`, `B2_REGION`
- Cloudinary: `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_CLOUD_NAME`
- Google Drive: `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_DRIVE_REFRESH_TOKEN`
- Supabase: `SUPABASE_PUBLISHABLE_KEY`

No AI-provider secret binding was found in the live Worker secret inventory.

## Supabase

Project: `Enterprise AI DMS` (`jkobgssaqifzrqfirdfu`)

- Status: ACTIVE_HEALTHY
- PostgreSQL: 17.6
- Security Advisor: one warning — leaked-password protection disabled.
- Performance Advisor: three unused indexes are informational; do not remove without workload evidence.
- Browser key boundary: use the publishable key; never expose a service-role/secret key.

## Render

One accessible workspace exists: `My Workspace`.

Service inspection is **not yet performed** because the Render connector requires explicit workspace selection before accessing services. Do not infer that services or keys are unused until that workspace is confirmed.

## Local .env

The repository contains only templates. The real `web-platform/backend/.env` is intentionally not committed.

Therefore:

- template keys can be audited;
- actual local key presence/validity cannot be proven from GitHub;
- do not paste real secrets into chat;
- when local execution is available, test provider connectivity without printing keys.

## Environment rules

1. Local mode must run with AI and cloud credentials absent.
2. Browser `VITE_*` values may only be intentionally public values.
3. Cloudflare/Render server secrets remain server-side.
4. A key's presence is not proof of validity; every enabled provider needs a health/test result.
5. Remove a variable only after code-reference audit + deployment-reference audit + runtime check.
