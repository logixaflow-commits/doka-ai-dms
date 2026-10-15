# Repository Structure — Doka

This is the current canonical layout for Doka's active code. It supersedes the previous generated, point-in-time repository tree. Local runtime data, dependency folders and historical material are intentionally not enumerated.

```text
doka-ai-dms/
├── apps/
│   ├── mobile/                         # Preserved/deferred mobile surface
│   └── web-platform/
│       ├── frontend/                   # React / Vite browser application
│       ├── backend/                    # FastAPI Personal Local runtime and shared services
│       │   ├── app/                    # FastAPI application
│       │   ├── cloudflare_worker/       # Active Cloudflare Worker and D1 migrations
│       │   └── supabase/               # Supabase configuration and migrations
│       └── tests/                      # Maintained web-platform regression tests
├── docs/                               # Current product, architecture, setup and operations docs
├── scripts/                            # Launch, verification and acceptance tooling
├── infrastructure/                     # Deferred/preserved infrastructure assets
├── .github/workflows/                  # CI and deployment automation
└── archive/                            # Historical and legacy material; not active runtime code
```

## Placement rules

- Keep browser code in `apps/web-platform/frontend/` and FastAPI/local runtime code in `apps/web-platform/backend/`.
- Keep Cloudflare Worker code, D1 migrations and Supabase assets under the backend boundary because they serve the web platform's server/data plane.
- `apps/mobile/` is preserved for a later mobile product. Do not infer that it is currently release-ready.
- A native desktop installer is not yet an application surface. Add `apps/desktop/` only when that implementation begins.
- Root Markdown files are project-wide status, policy and roadmap documents; detailed current guides belong in `docs/`.
- `archive/` remains historical evidence and must not be used as an active runtime path.

See `../PROJECT_OVERVIEW.md` for runtime boundaries, `../CURRENT_STATE.md` for evidence-backed status, and `../ROADMAP.md` for planned work.
