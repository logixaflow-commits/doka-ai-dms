# Doka Security and Deployment Controls

## Vercel deployment control

- **Owner-controlled Vercel state is authoritative.** If the owner disables, pauses, or closes Vercel, do **not** reactivate it, reconnect it, trigger a deployment, or change deployment settings unless the owner explicitly asks for Vercel to be reopened.
- Vercel may be temporarily reopened by the owner for a build check. During that window, treat **build-rate limits as an expected operational constraint** and do not repeatedly retry failed builds or create unnecessary deployments.
- The repository must not add a `vercel.json` that hard-codes Vercel dashboard overrides for `framework`, `installCommand`, `buildCommand`, or `outputDirectory`. The repository currently has **no `vercel.json`**.
- Current frontend root: `web-platform/frontend`. The frontend is a Vite application and its package scripts remain the source of truth for local/CI builds.
- A Vercel rate-limit failure is not a reason to weaken application security, change deployment architecture, or repeatedly trigger builds.

## Secret handling

- Never commit service-role, database-secret, AI-provider, or other server-only credentials.
- Browser-exposed `VITE_*` values must be limited to intentionally public configuration such as Supabase publishable configuration.
- Cloudflare Worker secrets remain in Cloudflare secret bindings.

## Production boundary

- Cloudflare Worker is the active cloud API.
- Supabase Auth, Postgres RLS, and private Storage remain ownership/security boundaries.
- Do not claim authenticated production readiness until real-user isolation and recovery acceptance tests are completed.
- The remaining Supabase Security Advisor warning is **Leaked Password Protection Disabled** until it is explicitly enabled and verified.

## Repository and branch control

- Production changes are consolidated on `main`.
- PR #17 is merged; PR #19 was reconciled into `main` and closed.
- The remaining `fix/*` branches are historical branches only. They may be deleted by the repository owner after confirming that `main` contains the required changes.
- Do not delete or recreate those branches as part of normal deployment work unless explicitly requested.

## Change discipline

- Make production changes on `main` only after verification.
- Keep deployment configuration minimal and avoid duplicated dashboard-vs-repository overrides.
- Re-run security, dependency, and production smoke checks after deployment-affecting changes.
- Do not mark the system production-ready merely because a CI or Cloudflare deployment is green; the real-user, isolation, recovery, OCR, backup, and security acceptance gates must also pass.
