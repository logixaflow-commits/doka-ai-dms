# Doka Deployment

> **Owner:** Where does Doka run and what deployment evidence is required?
> **Update when:** Runtime topology, Worker deployment, hosting provider state, migration evidence or release prerequisites change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Application architecture detail, secrets, or detailed incident procedures.

## Active topology
- Personal Local: FastAPI + React/Vite on the user's machine.
- Personal Cloud API: Cloudflare Worker doka-ai-dms.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: project is inactive in the connected account; explicit paused-state field is not exposed by the connected API, so owner-paused remains VERIFY.
- Render: the connected Render workspace returned no services on 2026-10-08; no active Render runtime was observed.

## Cloudflare Worker
Current URL: https://doka-ai-dms.logixaflow.workers.dev.

Live verification on 2026-10-08:
- Worker: doka-ai-dms
- Current traffic: 100%
- Version number: 591
- Version ID: a9fdc0ab-c0f6-49e0-a8bc-cc9017e867d5
- Version uploaded: 2026-10-07T20:11:13.465482Z
- Deployment created: 2026-10-07T20:11:26.087286Z

The Worker must authenticate cloud requests and must not proxy large document bytes unnecessarily. Direct upload sessions are used for provider-backed document bytes.

## Vercel
Connected Vercel project: enterprise-ai-dms.
Current observed state: live=false. Latest production deployment state: CANCELED.
The connected API did not expose an explicit paused-state property. Do not upgrade the historical owner-paused statement to VERIFIED without explicit dashboard/API evidence.

## Render
The connected Render workspace returned no services on 2026-10-08. This is evidence that no active Render service is visible to the connected account/workspace. No Render runtime is therefore treated as current deployment authority.

## Release evidence
Required before production sign-off: authenticated user lifecycle, two-user isolation, 50 MiB boundary, provider recovery drills, OCR benchmark, backup/recovery proof, Supabase security settings, and runtime monitoring evidence.

## Database migration distinction
Repository migration head: 20261007120000_doka_trigger_function_least_privilege.sql.
Last audited live Supabase head: 20261005113241_doka_audit_export_backup_actions.
These are separate facts; live state requires fresh verification before release.

## Deferred deployment references
Historical Render/FastAPI-cloud deployment instructions and older cloud-first architecture are preserved in archive/legacy. They are not current deployment authority.
