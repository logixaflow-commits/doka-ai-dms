#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Personal Local DMS - Startup"

command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required."; exit 1; }
NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
if [ "$NODE_MAJOR" != "24" ]; then
  echo "Node.js 24.x is required (found major version $NODE_MAJOR)."
  exit 1
fi

if [ ! -x "apps/web-platform/backend/.venv/bin/python" ]; then
  python3 -m venv apps/web-platform/backend/.venv
fi

if [ ! -f "apps/web-platform/backend/.env" ]; then
  cp apps/web-platform/backend/.env.example apps/web-platform/backend/.env
  echo "Created apps/web-platform/backend/.env. Set BOOTSTRAP_ADMIN_PASSWORD before login."
fi

apps/web-platform/backend/.venv/bin/python -m pip install -r apps/web-platform/backend/requirements-local.txt

if [ ! -d "apps/web-platform/frontend/node_modules" ]; then
  (cd apps/web-platform/frontend && npm ci)
fi

trap 'kill 0' EXIT
(cd apps/web-platform/backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
(cd apps/web-platform/frontend && npm run dev) &
wait
