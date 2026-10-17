> **Provider readiness snapshot — 2026-10-17 (current main `db76c9c`)**
>
> - Production Worker version 738 is live; health/config, unauthenticated-denial, allowed-origin CORS and untrusted-origin rejection passed. Current-main Production CI/CD, Doka Quality Checks, CodeQL, Worker deployment and live infrastructure smoke passed.
> - Dedicated staging Worker is deployed with staging-only Supabase/D1 and session secret. Staging health/config, preview-origin CORS GET and OPTIONS preflight passed. Staging currently has no B2, Cloudinary or Google Drive bindings.
> - Vercel production frontend is READY and the canonical homepage/JS return HTTP 200; production bundle points only at production Worker/Supabase. Preview points only at staging.
> - Independent checks: repository self-audit 23/23; Personal Local regression subset 138 passed; cloud-storage/provider contract tests 63 passed; frontend lint/build/smoke passed; npm install audit reported zero vulnerabilities.
> - **Full production acceptance remains blocked** on strict Myanmar/English OCR accuracy, full browser approval/final-copy/backup/isolated restore, measured RTO/RPO, authenticated staging A/B lifecycle/isolation, exact 50 MiB byte integrity, staging-only provider bindings/recovery, review of four staging SECURITY DEFINER advisor warnings, and the plan-blocked production leaked-password-protection setting.
> - Render is intentionally unused. The cloud API runtime is Cloudflare Worker, not the Personal Local FastAPI entry point.
>
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
