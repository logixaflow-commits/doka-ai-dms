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

## Code-scanning triage — 2026-10-07

The following paths were reviewed because they repeatedly appeared in CodeQL/code-scanning findings:

| Area | Decision |
|---|---|
| `app/api/routes/integrations.py` | Fixed: integration logs now require admin authorization. |
| `app/api/routes/monitoring.py` | Fixed: detailed health and Prometheus metrics now require admin authorization; basic health remains public for liveness checks. |
| `app/routes/advanced_reports.py` | Fixed: report template creation/listing/generation/export are admin-only because the service can read cross-user document/user/activity data. |
| `app/routes/external_integrations.py` | Fixed: external integration management and sync/log operations are admin-only. |
| `app/routes/workspace.py` | Reviewed: router has a local-workspace-user dependency and downstream session/path validation; no additional alert-driven change identified from source review. |
| `app/routes/rate_limiting.py` | Reviewed: user usage/quota reads are user-scoped and quota mutation is admin-only; no alert-driven security change identified. |
| `app/routes/document_versions.py` | Reviewed: document ownership/admin checks are present on version operations; no additional alert-driven change identified. |
| `app/routes/advanced_reports.py` / `services/advanced_reporting.py` | Cross-user reporting is now behind the admin route boundary. |
| `app/templates/dashboard.html` | Reviewed: document-derived UI values use DOM `textContent`/safe DOM construction rather than injecting untrusted HTML. |
| `app/api/routes/reports.py` | Reviewed: report IDs are UUID-validated and download lookup requires an exact filename match inside the reports directory. |
| `app/core/storage.py` | Reviewed: local storage paths are resolved and constrained beneath the configured root; storage keys use restricted components. |
| `app/services/cloud_storage.py` | Reviewed: object keys are normalized before provider access; SHA-256 is used for integrity and provider authentication where required. |
| `cloudflare_worker/storage_cloudinary.py` | Reviewed: SHA-256 is required by the Cloudinary signing protocol, not used for password storage; an in-source CodeQL rationale is present. |

Do not dismiss a new finding merely because it appears in one of these files. Re-check the exact rule and data flow first. Provider-protocol hashing findings should only be dismissed/suppressed when the exact alert is the documented Cloudinary signature use described above.
