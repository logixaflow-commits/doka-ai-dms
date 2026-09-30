# Repository Structure

## Current layout

```text
enterprise-ai-dms/
├── README.md
├── QUICKSTART.md
├── CONTRIBUTING.md
├── LICENSE
├── .github/
├── web-platform/
│   ├── frontend/        # React + Vite
│   ├── backend/         # FastAPI + Personal Local data plane
│   ├── tests/           # Personal Local tests
│   └── docs/            # documentation pointer
├── mobile/              # React Native / Expo legacy-deferred app
├── docs/
│   ├── product/         # reserved for product docs
│   ├── architecture/   # reserved for architecture docs
│   ├── guides/         # reserved for user/developer guides
│   ├── integrations/   # reserved for integration docs
│   └── legacy/          # historical enterprise docs
├── infrastructure/
│   ├── docker/
│   ├── monitoring/
│   ├── nginx/
│   ├── railway/
│   └── env/
├── scripts/             # maintenance/deployment helpers
└── archive/
    └── legacy-enterprise/
```

## Preservation rule

The restructuring is a path change, not a feature deletion. Existing application trees are moved as Git tree objects so their source blobs are preserved. Legacy enterprise modules remain available for later phases, while the default runtime stays focused on Personal Local.

## Runtime boundary

The supported current path is:

`web-platform/backend/app/main.py` → Personal Local FastAPI runtime

`web-platform/frontend` → Personal Local browser UI

Legacy entry points and deferred deployment assets are retained but are not loaded by the default startup scripts or CI checks.
