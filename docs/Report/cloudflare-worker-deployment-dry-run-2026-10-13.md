# Cloudflare Worker deployment dry-run — 2026-10-13

## Finding

The production deployment workflow pinned `workers-py==1.72.0`, which the package resolver could not find. The deploy command therefore failed before building the Worker. This was not covered by the standard quality workflow because the production deployment job is gated behind explicit confirmation.

## Fix

- Updated both deployment workflow invocations to pin `workers-py==1.17.7`, the version available from the package index and verified in the current environment.
- Kept production deployment gated: the workflow still requires the explicit `confirm_production` input for manual dispatch or the documented `[deploy-worker]` commit marker.

## Verification

- The previous pin `workers-py==1.72.0` failed dependency resolution.
- `uvx --from workers-py==1.17.7 pywrangler deploy --dry-run --config wrangler.jsonc` succeeded. Wrangler built the Python Worker bundle and exited without deploying.
- The build included the changed Google Drive provider and Worker source.
- Production was not deployed. Live health and authenticated Google Drive export still require a deployment and valid provider credentials.
