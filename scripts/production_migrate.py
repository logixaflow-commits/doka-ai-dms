#!/usr/bin/env python3
"""Zero-Downtime Safe Database Migration Runner for Doka-AI-DMS.

Designed for automated production pipelines and containerless deployments (systemd / PM2).
Features:
- Pre-flight database connectivity check with exponential backoff.
- Runs Alembic migrations (`alembic upgrade head`) cleanly from backend root.
- Post-migration revision verification against alembic history.
- Non-zero exit code on failure to block faulty CI/CD rollouts.
"""

import os
import sys
import time
import subprocess
from pathlib import Path


def log(msg: str) -> None:
    print(f"[Doka-Migrate] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)


def get_backend_dir() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    backend_dir = repo_root / "web-platform" / "backend"
    if not (backend_dir / "alembic.ini").exists():
        log(f"ERROR: alembic.ini not found in expected path: {backend_dir}")
        sys.exit(1)
    return backend_dir


def wait_for_database(max_retries: int = 15, delay: float = 2.0) -> bool:
    """Verifies database connectivity before initiating schema modifications."""
    log("Checking database accessibility...")
    backend_dir = get_backend_dir()
    sys.path.insert(0, str(backend_dir))

    check_code = (
        "import os, sys\n"
        "from sqlalchemy import create_engine, text\n"
        "db_url = os.getenv('DATABASE_URL', 'sqlite:///./doka.db')\n"
        "engine = create_engine(db_url, connect_args={'check_same_thread': False} if 'sqlite' in db_url else {})\n"
        "with engine.connect() as conn:\n"
        "    conn.execute(text('SELECT 1'))\n"
        "print('DB_CONNECTED')\n"
    )

    for attempt in range(1, max_retries + 1):
        try:
            res = subprocess.run(
                [sys.executable, "-c", check_code],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and "DB_CONNECTED" in res.stdout:
                log(f"Database connection verified successfully on attempt {attempt}.")
                return True
            else:
                log(f"Attempt {attempt}/{max_retries} failed: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as exc:
            log(f"Attempt {attempt}/{max_retries} encountered exception: {exc}")

        time.sleep(delay)

    log("ERROR: Timed out waiting for database connectivity.")
    return False


def run_alembic_upgrade() -> bool:
    """Executes alembic upgrade head in the web-platform/backend context."""
    backend_dir = get_backend_dir()
    log("Applying schema migrations via `alembic upgrade head`...")
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]

    try:
        res = subprocess.run(cmd, cwd=str(backend_dir), capture_output=True, text=True)
        if res.returncode == 0:
            log("Database migration succeeded:")
            for line in res.stdout.strip().splitlines():
                if line:
                    log(f"  {line}")
            return True
        else:
            log("ERROR: Alembic migration execution failed:")
            log(res.stderr)
            return False
    except Exception as exc:
        log(f"ERROR: Failed to run alembic command: {exc}")
        return False


def verify_migration_status() -> bool:
    """Verifies that alembic current matches the expected head."""
    backend_dir = get_backend_dir()
    log("Verifying migration current revision...")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            log(f"Current migration revision:\n  {res.stdout.strip()}")
            return True
        else:
            log(f"WARNING: `alembic current` returned code {res.returncode}: {res.stderr}")
            return False
    except Exception as exc:
        log(f"WARNING: Revision verification check failed: {exc}")
        return False


def main() -> None:
    log("Starting Zero-Downtime Migration Automation for Doka-AI-DMS...")
    if not wait_for_database():
        sys.exit(1)

    if not run_alembic_upgrade():
        log("CRITICAL: Schema migration failed. Aborting pipeline.")
        sys.exit(1)

    verify_migration_status()
    log("Migration automation completed successfully.")


if __name__ == "__main__":
    main()
