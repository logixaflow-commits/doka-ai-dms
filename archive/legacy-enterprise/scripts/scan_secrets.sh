#!/usr/bin/env bash
set -euo pipefail
echo "Scanning repository for common secret patterns (quick check)"

echo "-- Searching working tree for .env and secret-like filenames --"
git ls-files -oi --exclude-standard | grep -Ei "\.env|secret|credentials|\.pem|\.key" || true

echo "-- Grep for common key patterns in tracked files --"
git grep -nE "AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|SECRET|PASSWORD|PRIVATE_KEY|BEGIN RSA PRIVATE KEY|token=" || true

echo "-- Search full history for common key patterns (may be slow) --"
git rev-list --all | xargs -n1 -I{} git grep -nE "AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|BEGIN RSA PRIVATE KEY|PRIVATE_KEY|secret|token" {} || true

echo "Scan complete. If any hits appear, do NOT push until you remove them from history (use git filter-repo or BFG)."
