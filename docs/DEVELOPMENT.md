# Doka Development

## Prerequisites
- Python 3.12
- Node.js 24.x
- Git
- Tesseract for OCR testing

## Local development
Backend:
```sh
cd web-platform/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:
```sh
cd web-platform/frontend
npm ci
npm run dev
```

The frontend is Vite, not Next.js. The frontend package is React 19 + Vite 7 + Tailwind CSS 4.3.3.

## Validation
Run Python syntax/safety regression checks, frontend lint/build/smoke tests, and focused tests for changed boundaries. Cloud changes must preserve the Worker/storage/auth boundary.

## Branch policy
main is the consolidated development branch. Historical fix branches are preserved unless the repository owner explicitly removes them.

## Legacy code
Enterprise, mobile, infrastructure and older deployment code is preserved and must not be reintroduced into the Personal Local startup path without an explicit roadmap change.
