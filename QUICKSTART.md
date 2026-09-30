# Personal Local DMS — Quick Start

The current readiness target is the **Personal Local Edition**. It uses a React + Vite frontend and a FastAPI/Python backend. The original document source is treated as read-only.

## Prerequisites

- Python 3.12 recommended.
- Node.js 20+ for the Vite frontend.
- Tesseract OCR is optional for the first smoke test, but required for Myanmar/English OCR. On Windows, install Tesseract and make sure `tesseract --list-langs` includes `eng` and `mya`.
- Git.

You do **not** need PostgreSQL, Redis, MinIO, Supabase, Render, Vercel, or AI API keys for the Personal Local smoke test.

## First run on Windows

From the repository root:

```bat
start_application.bat
```

The script creates `web-platform\\backend\\.venv`, installs the smaller Personal Local dependency set, creates `web-platform\\backend\\.env` from the template, and starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:3000`

Before login, set `BOOTSTRAP_ADMIN_PASSWORD` in `web-platform\\backend\\.env`.

## Manual start

### Backend

```bat
cd web-platform\\backend
.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

In another terminal:

```bat
cd web-platform\\frontend
npm ci
npm run dev
```

The frontend is **Vite, not Next.js**. Its production build is `npm run build`.

## Safe test workflow

1. Create a small test source folder outside the workspace.
2. Put 5–20 copied representative documents inside it.
3. Set `SOURCE_ROOT` to that test folder.
4. Confirm `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false`.
5. Log in.
6. Open **Safe Workspace**.
7. Import → verify → scan → Read/OCR → Build Review Plan.
8. Review duplicate/version recommendations.
9. Approve only a small safe batch.
10. Confirm files are copied into `Final` and the source folder is unchanged.
11. Create and verify a backup.

## Important

Do not point `SOURCE_ROOT` at the real D: drive until the small-copy test passes.

The enterprise/cloud Docker, Railway, PostgreSQL, Redis, MinIO, and advanced modules remain in the repository as deferred legacy material; they are not required by the current Personal Local runtime.
