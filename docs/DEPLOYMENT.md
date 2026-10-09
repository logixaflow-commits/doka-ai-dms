# Doka Deployment

> **Owner:** Where does Doka run and what deployment evidence is required?
> **Update when:** Runtime topology, Worker deployment, hosting provider state, migration evidence or release prerequisites change.
> **Last Updated:** 2026-10-09
> **Do NOT put here:** Application architecture detail, secrets, or detailed incident procedures.

## Active topology
- Personal Local: FastAPI + React/Vite on the user's machine.
- Personal Cloud API: Cloudflare Worker doka-ai-dms.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: project is inactive in the connected account; explicit paused-state field is not exposed by the connected API, so owner-paused remains VERIFY.
- Render: the connected `My Workspace` service-list requests returned `null` on 2026-10-09 (with preview services both enabled and disabled); no service ID/configuration was visible to inspect. This is a connector visibility result, not proof that no service exists elsewhere. The repository contains Railway configuration files, but no evidence confirms Railway is the active runtime.

## Cloudflare Worker
Current URL: https://doka-ai-dms.logixaflow.workers.dev.

Live verification on 2026-10-09:
- Worker: doka-ai-dms
- Current traffic: 100%
- Version number: 671
- Version ID: 14e89790-c793-4d9b-9025-c5c7f412033f
- Deployment path: `.github/workflows/cloudflare-worker-deploy.yml` is the retained pinned, dry-run, explicit-confirmation deployment path. No production deployment was triggered during this review.
- Live CORS contract: explicit release/preview origins only with `allow_credentials=False`; the legacy `enterprise-ai-dms.vercel.app` origin is no longer present in the live bundle.

The Worker must authenticate cloud requests and must not proxy large document bytes unnecessarily. Direct upload sessions are used for provider-backed document bytes. A dedicated `DOKA_STORAGE_SESSION_SECRET` is now provisioned as a Worker secret; `DOKA_SINGLE_USER_EMAIL` remains intentionally enabled for the current single-user deployment.

## Vercel
Connected Vercel project: enterprise-ai-dms.
Current observed state: live=false. Latest production deployment state: CANCELED.
The connected API did not expose an explicit paused-state property. Do not upgrade the historical owner-paused statement to VERIFIED without explicit dashboard/API evidence.

## Render
The connected `My Workspace` service-list requests returned `null` on 2026-10-09, even with previews enabled. No service ID or environment configuration was returned, so the connected account view cannot currently support a safe Render change/deploy. Confirm the intended service in the Render Dashboard before adding secrets or deploying. Repository `infrastructure/railway/*` files are not proof that Railway is active and must not be used as the runtime authority without owner confirmation.

## Release evidence
Required before production sign-off: authenticated user lifecycle, two-user isolation, 50 MiB boundary, provider recovery drills, OCR benchmark, backup/recovery proof, Supabase security settings, and runtime monitoring evidence. D1 authorization-integrity migration 0002 has now been applied after a successful pre-change export/restore check; its seven expected index/trigger objects were verified in production and the affected metadata tables remain empty. The active document API still uses Supabase Postgres/Storage; D1 guard installation is not a substitute for Supabase RLS or two-user acceptance. Gate 9/10 execution uses the current direct-upload session/completion API and verifies actual downloaded bytes against SHA-256; it requires two pre-created user access tokens and an exact 50 MiB fixture for full closure. The runner must execute against a dedicated acceptance environment that allows both test users; production single-user restriction must not be weakened just to make the test pass. Gate 11 additionally requires live B2 and Google Drive recovery evidence and a real Cloudinary application-path check.

## Database migration distinction
Repository migration includes the reconciled least-privilege trigger migration `20261009083942_doka_trigger_function_least_privilege`.
Last verified live Supabase head on 2026-10-09: `20261009083942_doka_trigger_function_least_privilege`.
These are separate facts; live state requires fresh verification before release.

## Deferred deployment references
Historical Render/FastAPI-cloud deployment instructions and older cloud-first architecture are preserved in archive/legacy. They are not current deployment authority.
