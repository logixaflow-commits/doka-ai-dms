# Doka Deployment

## Active topology
- Personal Local: FastAPI + React/Vite on the user's machine.
- Personal Cloud API: Cloudflare Worker `doka-ai-dms`.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: owner-paused frontend target.
- Render: no active runtime verified.

## Cloudflare Worker
Current URL: `https://doka-ai-dms.logixaflow.workers.dev`.

The Worker must authenticate cloud requests and must not proxy large document bytes unnecessarily. Direct upload sessions are used for provider-backed document bytes.

## Vercel
Vercel is intentionally paused. Do not reactivate, reconnect, or deploy without explicit owner authorization. No repository `vercel.json` override is required.

## Release evidence
Required before production sign-off: authenticated user lifecycle, two-user isolation, 50 MiB boundary, provider recovery drills, OCR benchmark, backup/recovery proof, Supabase security settings, and runtime monitoring evidence.

## Database migration distinction
Repository migration head: `20261007120000_doka_trigger_function_least_privilege.sql`.
Previously audited live Supabase head: `20261005113241_doka_audit_export_backup_actions`.
These are separate facts; live state requires fresh verification before release.

## Deferred deployment references
Historical Render/FastAPI-cloud deployment instructions and older cloud-first architecture are preserved in archive/legacy. They are not current deployment authority.
