> **Provider readiness snapshot — 2026-10-17**
>
> - Vercel `enterprise-ai-dms` production deployment for main `ca38d52a3155785e83720edcb18e3de9497a0b86` is READY; the canonical homepage returned HTTP 200. Preview and production Supabase/Worker configuration must remain isolated.
> - Cloudflare scripts `doka-ai-dms` and `doka-ai-dms-staging` are deployed. Staging settings were freshly verified against Supabase project `gzxybtqquzycogaowdbj` and D1 `11baa497-e6f7-4054-8e9f-3a21baec93f3`; production uses production resources. Never run acceptance against production.
> - Production Worker last passed health/config/single-user smoke on source commit `3b29176a6329298205aa896eae7864ae4a8df4d9`; current main has a newer request-scoped CORS fix that is awaiting the guarded production rollout.
> - Supabase production and staging both report `ACTIVE_HEALTHY`. Production Security Advisor warns that leaked-password protection is disabled (plan-blocked). Staging Security Advisor warns on four authenticated-callable SECURITY DEFINER RPCs; explicit owner checks exist, but real authenticated A/B tests and review remain required.
> - Latest main Doka Quality Checks, Production CI/CD and CodeQL passed. The desktop Electron Dependabot security update failed because the package had no lockfile and a floating dependency range; the current follow-up pins Electron and adds desktop Dependabot updates.
> - Render `My Workspace` has no services and is intentionally unused; the documented cloud API runtime is Cloudflare Worker, not the Personal Local FastAPI entry point.
> - **Full production acceptance remains blocked** on strict Myanmar/English OCR benchmark, real browser approval/copy/backup/isolated restore, measured RTO/RPO, authenticated staging A/B lifecycle/isolation, exact 50 MiB byte integrity, B2/Cloudinary/Google Drive application-path recovery, and review of the staging RPC advisor warning.
>

# Doka Operations

> **Owner:** How is Doka operated, monitored and kept within its security/recovery boundaries?
> **Update when:** Runtime services, provider readiness, secrets handling, monitoring, incident response or operational runbooks change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Canonical architecture, detailed API contracts, or release roadmap ownership.

## Evidence vocabulary
Use DONE, VERIFIED, PENDING, BLOCKED, DEFERRED, NEXT and VERIFY. Never treat configuration as live proof.

## Current services
Cloudflare Worker `doka-ai-dms` is the active cloud API. Supabase is the active cloud identity/database/storage boundary. Vercel is owner-paused. No active Render runtime is verified.

## Secrets
Keep provider secrets server-side. Browser `VITE_*` variables may contain only intentionally public configuration. Never commit service-role, provider secret, OAuth refresh token or AI secret values.

## Monitoring and incident handling
Use application health/config endpoints and provider dashboards for live evidence. Preserve correlation identifiers where implemented. Investigate authentication, ownership, storage and recovery failures before retrying destructive operations.

## Provider readiness
Cloudinary, B2 and Google Drive are implemented/configuration-gated paths, not automatically production-proven. Real upload, integrity, cleanup and recovery evidence is required.

## Local operations
Operate Personal Local only against copied representative data during acceptance. Keep original source outside the writable workspace and maintain verified backups.

## Operational runbooks
Future detailed correlation-ID and threshold-tuning runbooks belong under `docs/runbooks/`.
