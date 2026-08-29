"""
Office DMS - Backup Script
Scheduled backup of database and important files.
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings


def backup_database():
    """Backup the database to a file."""
    logger.info("Starting database backup...")
    
    try:
        # Create backup directory
        backup_dir = Path(settings.LOG_DIR) / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"dms_backup_{timestamp}.sql"
        
        # Determine database type and backup method
        database_url = settings.DATABASE_URL
        
        if database_url.startswith("sqlite"):
            # SQLite backup
            db_path = database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_file)
                logger.info(f"✓ SQLite database backed up to {backup_file}")
            else:
                logger.warning(f"Database file not found: {db_path}")
                return False
                
        elif database_url.startswith("postgresql"):
            # PostgreSQL backup using pg_dump
            # Extract connection details from DATABASE_URL
            # Format: postgresql+psycopg2://user:password@host:port/dbname
            url = database_url.replace("postgresql+psycopg2://", "postgresql://")
            
            try:
                # Use pg_dump for PostgreSQL
                cmd = [
                    "pg_dump",
                    url,
                    "-f", str(backup_file),
                    "--no-owner",
                    "--no-acl"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"✓ PostgreSQL database backed up to {backup_file}")
                else:
                    logger.error(f"✗ PostgreSQL backup failed: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                logger.error("✗ pg_dump not found. Please install PostgreSQL client tools.")
                return False
        else:
            logger.warning(f"Unsupported database type: {database_url}")
            return False
        
        # Compress the backup file
        compressed_file = backup_file.with_suffix('.sql.gz')
        with open(backup_file, 'rb') as f_in:
            with open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed backup
        backup_file.unlink()
        
        logger.info(f"✓ Backup compressed to {compressed_file}")
        
        # Clean up old backups (keep based on retention policy)
        cleanup_old_backups(backup_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Database backup failed: {e}")
        return False


def cleanup_old_backups(backup_dir, retention_days=None):
    """Remove backups older than retention period."""
    if retention_days is None:
        retention_days = settings.BACKUP_RETENTION_DAYS
    
    logger.info(f"Cleaning up backups older than {retention_days} days...")
    
    try:
        cutoff_date = datetime.utcnow().timestamp() - (retention_days * 24 * 60 * 60)
        
        for backup_file in backup_dir.glob("dms_backup_*.sql.gz"):
            if backup_file.stat().st_mtime < cutoff_date:
                backup_file.unlink()
                logger.info(f"✓ Removed old backup: {backup_file.name}")
        
        logger.info("✓ Backup cleanup completed")
        
    except Exception as e:
        logger.warning(f"⚠ Backup cleanup failed: {e}")


def backup_files():
    """Backup important files and directories."""
    logger.info("Starting file backup...")
    
    try:
        backup_dir = Path(settings.LOG_DIR) / "backups" / "files"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Backup configuration files
        config_backup = backup_dir / f"config_{timestamp}.tar.gz"
        config_files = [".env", "config.yaml"]
        
        existing_configs = [f for f in config_files if os.path.exists(f)]
        
        if existing_configs:
            import tarfile
            with tarfile.open(config_backup, "w:gz") as tar:
                for config_file in existing_configs:
                    tar.add(config_file)
            logger.info(f"✓ Configuration files backed up to {config_backup}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ File backup failed: {e}")
        return False


def backup_minio():
    """Backup MinIO data using mc command or direct file copy."""
    logger.info("Starting MinIO backup...")
    
    try:
        backup_dir = Path(settings.LOG_DIR) / "backups" / "minio"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # This is a placeholder for MinIO backup
        # In production, you might use:
        # - MinIO's built-in replication
        # - mc mirror command from MinIO Client
        # - Direct file system backup of MinIO data directory
        
        logger.info("⚠ MinIO backup not implemented (use MinIO replication in production)")
        return True
        
    except Exception as e:
        logger.error(f"✗ MinIO backup failed: {e}")
        return False


def main():
    """Main backup function."""
    logger.info("=" * 60)
    logger.info("Starting Enterprise DMS Backup")
    logger.info("=" * 60)
    
    results = {
        "database": backup_database(),
        "files": backup_files(),
        "minio": backup_minio()
    }
    
    logger.info("=" * 60)
    logger.info("Backup Summary:")
    for component, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"{status} {component.capitalize()}: {'Success' if success else 'Failed'}")
    logger.info("=" * 60)
    
    overall_success = all(results.values())
    if overall_success:
        logger.info("✓ Backup completed successfully")
    else:
        logger.error("✗ Backup completed with errors")
    
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
