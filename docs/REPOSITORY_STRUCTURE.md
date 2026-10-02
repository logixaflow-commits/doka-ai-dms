# Doka Repository Structure

## Active application boundary

The supported product target is **Doka Personal Local Edition**. Keep active runtime code, tests, and their documentation grouped under `web-platform/`.

```text
enterprise-ai-dms/
├── .github/
│   ├── dependabot.yml
│   └── workflows/              # CI and quality checks
├── archive/
│   └── legacy-enterprise/      # preserved historical implementation
├── docs/                       # current product, setup, security and phase docs
│   └── legacy/                 # historical enterprise documentation
├── infrastructure/             # deferred deployment and operations assets
├── mobile/                     # preserved, deferred mobile application
├── scripts/                    # repository-level validation/maintenance scripts
├── supabase/
│   └── migrations/             # database migrations for optional cloud features
├── web-platform/
│   ├── backend/                # FastAPI Personal Local runtime and supporting modules
│   ├── frontend/               # React + TypeScript + Vite UI
│   ├── tests/                  # Personal Local regression tests
│   └── docs/                   # web-platform documentation pointers
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── QUICKSTART.md
├── README.md
├── start_application.bat       # primary Windows local launcher
├── start_backend.bat
├── start_frontend.bat
├── run.bat / run.sh            # retained legacy launchers; verify before use
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
