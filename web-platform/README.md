# Web Platform

The current Personal Local Edition lives under this boundary.

- `frontend/` — React + Vite browser application.
- `backend/` — FastAPI/Python local data-plane application.
- `tests/` — Personal Local regression tests.
- `docs/` — web-platform-specific documentation pointers.

The backend keeps legacy enterprise modules in the same source tree for later reuse, but the default runtime is the Personal Local entry point.


## Personal Local build contract

For a production-built Personal Local frontend, set `VITE_DOKA_EDITION=personal-local` at frontend build time. Keep this flag unset for cloud/Vercel builds. The backend must run with `ENVIRONMENT=local` or `development` for local password authentication and filesystem workspace routes. Do not configure real Supabase credentials when expecting Personal Local password authentication; configured Supabase takes precedence over the local auth path. Keep `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false` in all Personal Local deployments.
