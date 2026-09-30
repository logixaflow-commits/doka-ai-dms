# Contributing to Enterprise AI DMS

## Current development target

The active implementation target is the **Personal Local Edition** on the default `main` branch.

Keep the current safety boundary intact:

- Original source folders are read-only.
- Writable document operations stay inside the configured workspace.
- Organization copies approved files into Final; it does not modify the original source.
- AI is optional and disabled by default.
- Enterprise/cloud modules are preserved but should not be reintroduced into the Personal Local startup path unless explicitly planned.

## Development prerequisites

- Python 3.12
- Node.js 20+
- Git
- Tesseract OCR for OCR testing

## Validation

Before considering a Personal Local change complete:

1. Run Python syntax checks.
2. Run the local safety regression tests.
3. Run the frontend build and smoke test.
4. Verify that the Personal Local FastAPI entry point starts.
5. Verify that the frontend only calls endpoints exposed by the Personal Local runtime.
6. For document workflow changes, test against copied sample data and confirm the source remains unchanged.

The current CI workflow is `.github/workflows/local-core-check.yml`.

## Legacy enterprise code

The repository still contains enterprise routes, services, deployment configurations, mobile code, and historical documentation for later reuse. Do not delete these simply because they are not loaded by the Personal Local runtime. Keep them behind the documented legacy/deferred boundary.
