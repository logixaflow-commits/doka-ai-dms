#!/usr/bin/env bash
set -euo pipefail

# Final acceptance runner for Gates 3-6. It never asks Doka to write to the
# supplied source. Set these environment variables before running:
#   DOKA_PILOT_SOURCE   copied representative office dataset
#   DOKA_PILOT_WORKSPACE dedicated empty workspace
#   DOKA_PILOT_BACKUPS dedicated backup directory
#   DOKA_OCR_ROOT       copied OCR benchmark samples
#   DOKA_OCR_MANIFEST   manifest for those samples
#   BOOTSTRAP_ADMIN_PASSWORD local acceptance password (never committed)
# Optional:
#   DOKA_E2E_SOURCE_DIR defaults to DOKA_PILOT_SOURCE

: "${DOKA_PILOT_SOURCE:?Set DOKA_PILOT_SOURCE to a COPY of representative office data}"
: "${DOKA_PILOT_WORKSPACE:?Set DOKA_PILOT_WORKSPACE to an EMPTY dedicated workspace}"
: "${DOKA_PILOT_BACKUPS:?Set DOKA_PILOT_BACKUPS to a dedicated backup directory}"
: "${DOKA_OCR_ROOT:?Set DOKA_OCR_ROOT to copied OCR samples}"
: "${DOKA_OCR_MANIFEST:?Set DOKA_OCR_MANIFEST to the OCR manifest JSON}"
: "${BOOTSTRAP_ADMIN_PASSWORD:?Set BOOTSTRAP_ADMIN_PASSWORD for this acceptance run}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/web-platform/backend"
FRONTEND="$ROOT/web-platform/frontend"
VENV="$ROOT/.acceptance-venv"
EVIDENCE="$ROOT/Phase0_Evidence/acceptance"
mkdir -p "$EVIDENCE"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$BACKEND/requirements-local.txt" -r "$BACKEND/requirements-test.txt"

export ENVIRONMENT=development
export DEBUG=false
export SECRET_KEY="${SECRET_KEY:-$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')}"
export SOURCE_ROOT="$DOKA_PILOT_SOURCE"
export WORKING_ROOT="$DOKA_PILOT_WORKSPACE"
export FINAL_ROOT="$DOKA_PILOT_WORKSPACE/Final"
export QUARANTINE_ROOT="$DOKA_PILOT_WORKSPACE/Quarantine"
export BACKUP_ROOT="$DOKA_PILOT_BACKUPS"
export ORIGINAL_READ_ONLY=true
export ALLOW_SOURCE_WRITE=false
export BOOTSTRAP_ADMIN_PASSWORD
export LOCAL_ADMIN_USERNAME="${LOCAL_ADMIN_USERNAME:-admin}"
export CORS_ORIGINS="http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000"

"$VENV/bin/python" "$ROOT/scripts/ocr_benchmark.py" \
  --root "$DOKA_OCR_ROOT" \
  --manifest "$DOKA_OCR_MANIFEST" \
  --output "$EVIDENCE/gate-3-ocr.json"

"$VENV/bin/python" "$ROOT/scripts/doka_pilot_check.py" \
  --source "$DOKA_PILOT_SOURCE" \
  --workspace "$DOKA_PILOT_WORKSPACE" \
  --backup-root "$DOKA_PILOT_BACKUPS" \
  --output "$EVIDENCE/gate-5-pilot-gate-6-recovery.json" \
  --require-ocr

cd "$FRONTEND"
npm ci
npx playwright install chromium
npm run build

export DOKA_E2E_SOURCE_DIR="${DOKA_E2E_SOURCE_DIR:-$DOKA_PILOT_SOURCE}"
export DOKA_E2E_USERNAME="${DOKA_E2E_USERNAME:-$LOCAL_ADMIN_USERNAME}"
export DOKA_E2E_PASSWORD="$BOOTSTRAP_ADMIN_PASSWORD"

"$VENV/bin/python" -m uvicorn app.main:app --app-dir "$BACKEND" --host 127.0.0.1 --port 8000 >"$EVIDENCE/backend.log" 2>&1 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

npm run dev -- --host 127.0.0.1 --port 3000 >"$EVIDENCE/frontend.log" 2>&1 &
FRONTEND_PID=$!
trap 'kill "$FRONTEND_PID" 2>/dev/null || true; kill "$BACKEND_PID" 2>/dev/null || true' EXIT

READY=0
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null && curl -fsS http://127.0.0.1:3000/login >/dev/null; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "$READY" != "1" ]]; then
  echo "Personal Local acceptance services did not become healthy within 60 seconds." >&2
  tail -n 80 "$EVIDENCE/backend.log" "$EVIDENCE/frontend.log" >&2 || true
  exit 1
fi

npm run test:e2e:local
