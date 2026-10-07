# Doka Security and Deployment Controls

## Vercel deployment control
- Owner-controlled Vercel state is authoritative. Do not reactivate it, reconnect it, trigger a deployment, or change deployment settings unless the owner explicitly asks.
- Vercel rate-limit failures are operational constraints and are not a reason to weaken security or repeatedly trigger builds.
- The repository must not add a vercel.json override for framework/install/build/output settings.
- Frontend root is web-platform/frontend and is a Vite application.
- A Vercel build failure is not a reason to change application security or architecture.

## Secret handling
- Never commit service-role, database-secret, AI-provider, or other server-only credentials.
- Browser-exposed VITE_* values must be intentionally public configuration only.
- Cloudflare Worker secrets remain in secret bindings.

## Production boundary
- Cloudflare Worker is the active cloud API.
- Supabase Auth, Postgres RLS, and private Storage remain ownership/security boundaries.
- Do not claim authenticated production readiness until real-user isolation and recovery tests are complete.
- Supabase Security Advisor still has leaked-password protection disabled until explicitly enabled and verified.

## Repository and branch control
- Production changes are consolidated on main.
- PR #17 is merged and PR #19 was reconciled into main and closed.
- Historical fix branches may only be removed by the repository owner.

## Change discipline
- Verify before production changes.
- Keep deployment configuration minimal.
- Re-run security, dependency and production smoke checks after deployment-affecting changes.
- CI/Cloudflare green does not equal production readiness.

## Code-scanning triage — 2026-10-07
Reviewed/fixed or reviewed CodeQL-sensitive areas included integrations authorization, monitoring authorization, advanced report admin boundaries, external integration admin boundaries, workspace/path validation, rate limiting, document version ownership, dashboard safe DOM construction, report UUID/filename validation, local storage path confinement, cloud storage object-key normalization and Cloudinary signature hashing rationale.

New findings must be re-checked by exact rule/data flow; provider-protocol hashing must not be dismissed generically.
