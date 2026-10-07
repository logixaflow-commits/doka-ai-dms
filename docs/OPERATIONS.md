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
