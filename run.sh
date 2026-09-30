#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Personal Local DMS - Startup"

command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required."; exit 1; }

if [ ! -x "dms/.venv/bin/python" ]; then
  python3 -m venv dms/.venv
fi

if [ ! -f "dms/.env" ]; then
  cp dms/.env.example dms/.env
  echo "Created dms/.env. Set BOOTSTRAP_ADMIN_PASSWORD before login."
fi

dms/.venv/bin/python -m pip install -r dms/requirements-local.txt

if [ ! -d "app/node_modules" ]; then
  (cd app && npm ci)
fi

trap 'kill 0' EXIT
(cd dms && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
(cd app && npm run dev) &
wait
