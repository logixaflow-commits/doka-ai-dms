#!/usr/bin/env python3
"""
Office DMS - Database Backup Script
Supports both SQLite and PostgreSQL backups.
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def backup_sqlite():
    """Backup SQLite database."""
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "").replace("./", ""))
    if not db_path.exists():
        logger.error(f"SQLite database not found: {db_path}")
        return None

    backup_dir = Path(settings.ORGANIZED_ROOT).parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"dms_backup_{timestamp}.db"

    shutil.copy2(str(db_path), str(backup_path))
    logger.info(f"SQLite backup created: {backup_path}")
    return str(backup_path)


def backup_postgresql():
    """Backup PostgreSQL database using pg_dump."""
    backup_dir = Path(settings.ORGANIZED_ROOT).parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"dms_backup_{timestamp}.sql"

    # Parse DATABASE_URL
    # Format: postgresql+psycopg2://user:pass@host:port/dbname
    url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

    env = os.environ.copy()

    try:
        result = subprocess.run(
            ["pg_dump", "--dbname", url, "-f", str(backup_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0:
            logger.info(f"PostgreSQL backup created: {backup_path}")
            return str(backup_path)
        else:
            logger.error(f"pg_dump failed: {result.stderr}")
            return None
    except FileNotFoundError:
        logger.error("pg_dump not found. Install PostgreSQL client tools.")
        return None


def cleanup_old_backups():
    """Remove backups older than retention period."""
    backup_dir = Path(settings.ORGANIZED_ROOT).parent / "backups"
    if not backup_dir.exists():
        return

    cutoff = datetime.utcnow() - timedelta(days=settings.BACKUP_RETENTION_DAYS)
    deleted = 0

    for backup_file in backup_dir.glob("dms_backup_*"):
        if datetime.fromtimestamp(backup_file.stat().st_ctime) < cutoff:
            backup_file.unlink()
            deleted += 1

    if deleted > 0:
        logger.info(f"Deleted {deleted} old backup(s)")


def run_backup():
    """Run the full backup process."""
    logger.info("Starting database backup...")

    if settings.DATABASE_URL.startswith("sqlite"):
        result = backup_sqlite()
    else:
        result = backup_postgresql()

    if result:
        cleanup_old_backups()
        logger.info(f"Backup complete: {result}")
    else:
        logger.error("Backup failed")

    return result


if __name__ == "__main__":
    run_backup()
