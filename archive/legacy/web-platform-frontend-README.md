# Doka Personal Local — Frontend

React 19 + TypeScript + Vite frontend for the Doka Document Management System. The current Personal Local browser application is maintained in this directory.

## Requirements

- Node.js 24.x (enforced by `package.json`)
- npm

## Install and run

From the repository root:

```sh
cd web-platform/frontend
npm ci
npm run dev
```

Vite listens on `127.0.0.1:3000` by default. The development server proxies `/api` and `/health` to the local FastAPI backend at `127.0.0.1:8000`. Start the backend separately from `web-platform/backend`, or use the root launcher (`run.sh` / `start_application.bat`).

## Edition configuration

For a production-built Personal Local frontend, set:

```sh
VITE_DOKA_EDITION=personal-local
```

This build-time flag enables the explicit Personal Local auth/navigation boundary. Do not add Supabase service credentials or secrets to frontend environment variables: Vite-exposed variables are bundled for browser use. Keep cloud builds and cloud API configuration separate from the Personal Local edition.

## Quality checks

Run from this directory:

```sh
npm run lint
npm run build
npm test
```

- `lint` runs ESLint over the frontend source.
- `build` runs TypeScript project checks followed by the Vite production build.
- `test` runs the repository's frontend smoke/regression assertions in `scripts/smoke-test.mjs`.

These checks are separate: a smoke-test pass does not imply lint or TypeScript/build success. Record the actual command output; do not infer successful verification from the existence of the scripts.

## Important boundaries

- Personal Local data operations are handled by the local FastAPI backend; browser code must not write directly to Supabase REST or Storage endpoints.
- Keep authentication tokens and document/API responses out of Service Worker caches.
- Original source data remains read-only. Import and review flows operate on an isolated working copy.
- Use copied fixtures for development and tests. A real-office pilot requires a separate representative copy and the Phase 2 pilot procedure in the unified remediation roadmap.
