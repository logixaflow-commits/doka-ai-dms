> **Provider readiness snapshot — 2026-10-17**
>
> - Vercel production for main `777b37cc1f443fd367b81e0b38aacd7e1b9f16b9` is READY; canonical homepage and built JS asset returned HTTP 200. Production and Preview bundles are verified to reference only their matching Worker/Supabase environments.
> - Cloudflare production Worker `doka-ai-dms` was redeployed from the same main commit. Guarded deploy, health/config/single-user checks and live smoke passed. Live smoke confirms production origins are allowed, untrusted origin is denied, and unauthenticated document listing returns HTTP 401.
> - Cloudflare staging Worker and staging D1/Supabase bindings are present. Staging health/config/preview-origin CORS GET + OPTIONS smoke passed; staging RPC hardening remains staging-only.
> - Supabase production and staging both report `ACTIVE_HEALTHY`. Production Security Advisor warns that leaked-password protection is disabled (plan-blocked). Staging Security Advisor warns on four authenticated-callable SECURITY DEFINER RPCs; explicit owner checks exist, but real authenticated A/B tests and review remain required.
> - Exact-HEAD Doka Quality Checks, Production CI/CD, CodeQL, Dependency Review and desktop Electron smoke passed. Electron and electron-builder are pinned and desktop dependency updates are covered.
> - Render `My Workspace` has no services and is intentionally unused; the documented cloud API runtime is Cloudflare Worker, not the Personal Local FastAPI entry point.
> - **Full production acceptance remains blocked** on strict Myanmar/English OCR benchmark, real browser approval/copy/backup/isolated restore, measured RTO/RPO, authenticated staging A/B lifecycle/isolation, exact 50 MiB byte integrity, staging-only B2/Cloudinary/Google Drive bindings and application-path recovery, and review of the staging RPC advisor warning.

# Doka Operations

> **Owner:** How is Doka operated, monitored and kept within its security/recovery boundaries?
> **Update when:** Runtime services, provider readiness, secrets handling, monitoring, incident response or operational runbooks change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Canonical architecture, detailed API contracts, or release roadmap ownership.

## Evidence vocabulary
Use DONE, VERIFIED, PENDING, BLOCKED, DEFERRED, NEXT and VERIFY. Never treat configuration as live proof.

## Current services
Cloudflare Worker `doka-ai-dms` is the active cloud API. Supabase is the active cloud identity/database/storage boundary. Vercel Git integration is the active frontend deployment path; production is READY and the canonical alias returns HTTP 200. No active Render runtime is verified.

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
