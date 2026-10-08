#!/usr/bin/env python3
"""Privacy-safe live D1 job-idempotency acceptance.

Requires:
  CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_API_TOKEN
  DOKA_D1_DATABASE_ID

The database must already contain the reviewed Doka migrations. The script
creates only disposable acceptance rows, verifies duplicate convergence,
success, retry, and exhaustion/dead transitions, then removes those rows.
No credential values or payload contents are written to the evidence file.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

def query(account_id: str, database_id: str, token: str, sql: str, params: list[object] | None = None):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
    body = json.dumps({"sql": sql, "params": params or []}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError("Cloudflare D1 request failed") from exc
    if not payload.get("success"):
        raise RuntimeError("Cloudflare D1 query returned an error")
    return payload.get("result", [{}])[0]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    database_id = os.getenv("DOKA_D1_DATABASE_ID", "").strip()
    if not account_id or not token or not database_id:
        raise SystemExit("required Cloudflare D1 runtime credentials are missing")

    suffix = secrets.token_hex(8)
    job_id = f"acceptance-{suffix}"
    key = f"acceptance:{suffix}"
    dead_id = f"acceptance-dead-{suffix}"
    dead_key = f"acceptance-dead:{suffix}"
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    checks: dict[str, bool] = {}
    try:
        query(account_id, database_id, token,
              """INSERT INTO jobs (id, job_type, status, idempotency_key, payload_json, max_attempts)
                 VALUES (?, 'acceptance', 'pending', ?, ?, 2)""",
              [job_id, key, '{"acceptance":true}'])
        first = query(account_id, database_id, token,
                      "SELECT id,status,idempotency_key,payload_json,attempts,max_attempts FROM jobs WHERE idempotency_key=?",
                      [key])
        query(account_id, database_id, token,
              """INSERT INTO jobs (id, job_type, status, idempotency_key, payload_json, max_attempts)
                 VALUES (?, 'acceptance', 'pending', ?, ?, 2)
                 ON CONFLICT(idempotency_key) DO NOTHING""",
              [f"{job_id}-duplicate", key, '{"acceptance":true}'])
        second = query(account_id, database_id, token,
                       "SELECT id,status,idempotency_key,payload_json,attempts,max_attempts FROM jobs WHERE idempotency_key=?",
                       [key])
        checks["duplicate_converges"] = first["results"][0]["id"] == second["results"][0]["id"]

        query(account_id, database_id, token,
              "UPDATE jobs SET status='succeeded', result_json=?, updated_at=? WHERE id=? AND status='pending'",
              ['{"accepted":true}', now, job_id])
        terminal = query(account_id, database_id, token,
                         "SELECT status FROM jobs WHERE id=?", [job_id])
        checks["success_terminal"] = terminal["results"][0]["status"] == "succeeded"

        query(account_id, database_id, token,
              """INSERT INTO jobs (id, job_type, status, idempotency_key, payload_json, attempts, max_attempts)
                 VALUES (?, 'acceptance', 'processing', ?, ?, 1, 2)""",
              [dead_id, dead_key, '{"acceptance":true}'])
        query(account_id, database_id, token,
              "UPDATE jobs SET status='pending', attempts=attempts+1, last_error=?, updated_at=? WHERE id=? AND status='processing'",
              ["transient acceptance failure", now, dead_id])
        query(account_id, database_id, token,
              "UPDATE jobs SET status='dead', attempts=attempts+1, last_error=?, updated_at=? WHERE id=? AND status='pending'",
              ["exhausted acceptance failure", now, dead_id])
        dead = query(account_id, database_id, token, "SELECT status,attempts FROM jobs WHERE id=?", [dead_id])
        checks["retry_exhaustion_dead"] = dead["results"][0]["status"] == "dead" and int(dead["results"][0]["attempts"]) == 3
    finally:
        try:
            query(account_id, database_id, token, "DELETE FROM jobs WHERE id IN (?, ?)", [job_id, dead_id])
        except RuntimeError:
            pass

    evidence = {
        "schema_version": 1,
        "timestamp_utc": now,
        "checks": checks,
        "passed": all(checks.values()),
        "privacy": {
            "credentials_recorded": False,
            "database_id_recorded": False,
            "payload_recorded": False,
            "test_ids_recorded": False,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
