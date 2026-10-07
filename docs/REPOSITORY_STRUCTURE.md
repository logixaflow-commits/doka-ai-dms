# Doka Repository Structure

## Active application boundary

The repository root uses `MASTER-ROADMAP.md` as the documentation/status front door. Detailed active docs live under `docs/`; superseded plans live under `docs/legacy/`.

The supported product target is **Doka Personal Local Edition**. Keep active runtime code, tests, and their documentation grouped under `web-platform/`.

```text
enterprise-ai-dms/
├── .github/
│   ├── dependabot.yml
│   └── workflows/              # CI and quality checks
├── archive/                    # preserved legacy code and retired deployment assets
├── cloudflare_worker/           # active Cloudflare Worker API for cloud documents
├── docs/                        # current product, setup, security and phase docs
│   └── legacy/                 # historical/superseded documentation
├── infrastructure/             # deferred deployment and operations assets
├── mobile/                      # preserved, deferred mobile application
├── shared/                      # shared contracts/utilities; verify consumers before moving
├── scripts/                    # repository-level validation/maintenance scripts
├── supabase/
│   └── migrations/             # database migrations for optional cloud features
├── web-platform/
│   ├── backend/                # FastAPI Personal Local runtime and supporting modules
│   ├── frontend/               # React + TypeScript + Vite UI
│   ├── tests/                  # Personal Local regression tests
│   └── docs/                   # web-platform documentation pointers
├── .gitignore
├── .editorconfig / .gitattributes
├── pyproject.toml              # Cloudflare Worker package metadata and build configuration
├── wrangler.jsonc              # active Cloudflare Worker deployment configuration
├── CONTRIBUTING.md
├── LICENSE
├── QUICKSTART.md
├── README.md
├── start_application.bat       # current Windows local launcher
├── start_backend.bat            # backend-only Windows launcher
├── start_frontend.bat           # frontend-only Windows launcher
├── run.sh                       # current Linux/macOS local launcher
├── run.bat                      # Windows compatibility alias for start_application.bat
└── vercel.json                 # retained deployment configuration
```

## Runtime boundary

- Backend entry point: `web-platform/backend/app/main.py`.
- Frontend application: `web-platform/frontend/`.
- Personal Local tests: `web-platform/tests/`.
- The active product must keep source documents read-only and confine writable organization paths to the configured workspace.
- AI and cloud integrations remain optional and must not become prerequisites for the local-first runtime.
- `archive/`, `infrastructure/`, and `mobile/` are preserved/deferred areas. Do not delete or reconnect them to the Personal Local startup path as part of routine cleanup.

## Repository hygiene rules

1. Keep root limited to project entry points, repository configuration, and high-level documentation.
2. Put application code and application-specific dependencies inside `web-platform/`.
3. Put repository-wide scripts in `scripts/`; put tests beside the application boundary they validate.
4. Keep secrets, local databases, uploads, generated builds, logs, and user documents out of Git.
5. Prefer small, path-scoped changes. Do not move or rename existing assets without checking all launchers, CI workflows, and deployment configuration first.
6. Update this document whenever a top-level directory or runtime boundary changes.

## Documentation map

Current documentation source-of-truth files are indexed by `docs/DOKA_DOCUMENTATION_INDEX.md`. Start from root `MASTER-ROADMAP.md`; active UI, architecture, tools, environment and AI boundaries are maintained in their focused docs. Detailed execution remains in `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`.

The repository currently has no root `vercel.json`; Vercel configuration is intentionally kept out of the repository unless explicitly required and reviewed.
