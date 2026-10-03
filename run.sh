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

if [ ! -x "web-platform/backend/.venv/bin/python" ]; then
  python3 -m venv web-platform/backend/.venv
fi

if [ ! -f "web-platform/backend/.env" ]; then
  cp web-platform/backend/.env.example web-platform/backend/.env
  echo "Created web-platform/backend/.env. Set BOOTSTRAP_ADMIN_PASSWORD before login."
fi

web-platform/backend/.venv/bin/python -m pip install -r web-platform/backend/requirements-local.txt

if [ ! -d "web-platform/frontend/node_modules" ]; then
  (cd web-platform/frontend && npm ci)
fi

trap 'kill 0' EXIT
(cd web-platform/backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
(cd web-platform/frontend && npm run dev) &
wait
