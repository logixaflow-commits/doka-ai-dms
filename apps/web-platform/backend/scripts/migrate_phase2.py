"""
Migration Script: Phase 2 - 2FA and Folder Permissions
This script adds the necessary database changes for Phase 2 upgrade.

Run this script directly: python scripts/migrate_phase2.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base
from app.models.database import User, FolderPermission, UserFolderMapping
from loguru import logger


def migrate_2fa_fields():
    """Add 2FA fields to users table."""
    db = SessionLocal()
    try:
        # Check if columns exist
        inspector = engine.dialect.get_inspector(engine)
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        if 'totp_secret' not in column_names:
            logger.info("Adding totp_secret column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN totp_secret VARCHAR(32)"))
            db.commit()
            logger.info("✓ totp_secret column added")
        else:
            logger.info("totp_secret column already exists")
        
        if 'totp_enabled' not in column_names:
            logger.info("Adding totp_enabled column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE"))
            db.commit()
            logger.info("✓ totp_enabled column added")
        else:
            logger.info("totp_enabled column already exists")
        
        if 'backup_codes' not in column_names:
            logger.info("Adding backup_codes column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN backup_codes TEXT"))
            db.commit()
            logger.info("✓ backup_codes column added")
        else:
            logger.info("backup_codes column already exists")
        
        if 'failed_otp_attempts' not in column_names:
            logger.info("Adding failed_otp_attempts column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN failed_otp_attempts INTEGER DEFAULT 0"))
            db.commit()
            logger.info("✓ failed_otp_attempts column added")
        else:
            logger.info("failed_otp_attempts column already exists")
        
        if 'otp_locked_until' not in column_names:
            logger.info("Adding otp_locked_until column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN otp_locked_until TIMESTAMP"))
            db.commit()
            logger.info("✓ otp_locked_until column added")
        else:
            logger.info("otp_locked_until column already exists")
        
    except Exception as e:
        logger.error(f"Error adding 2FA fields: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_folder_permissions_table():
    """Create folder_permissions table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'folder_permissions' not in tables:
            logger.info("Creating folder_permissions table...")
            
            # Create table using SQL for compatibility
            db.execute(text("""
                CREATE TABLE folder_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    permission VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_folder_permissions_path ON folder_permissions(folder_path)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_folder_permissions_path ON folder_permissions(folder_path)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_folder_permissions_role ON folder_permissions(role)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_folder_permissions_role ON folder_permissions(role)"))
                except Exception:
                    pass
                    
            db.commit()
            logger.info("✓ folder_permissions table created")
        else:
            logger.info("folder_permissions table already exists")
        
    except Exception as e:
        logger.error(f"Error creating folder_permissions table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_user_folder_mappings_table():
    """Create user_folder_mappings table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'user_folder_mappings' not in tables:
            logger.info("Creating user_folder_mappings table...")
            
            db.execute(text("""
                CREATE TABLE user_folder_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    assigned_by INTEGER,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (permission_id) REFERENCES folder_permissions(id),
                    UNIQUE(user_id, permission_id)
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_user_folder_mappings_user_id ON user_folder_mappings(user_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_user_folder_mappings_user_id ON user_folder_mappings(user_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_user_folder_mappings_permission_id ON user_folder_mappings(permission_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_user_folder_mappings_permission_id ON user_folder_mappings(permission_id)"))
                except Exception:
                    pass
                    
            db.commit()
            logger.info("✓ user_folder_mappings table created")
        else:
            logger.info("user_folder_mappings table already exists")
        
    except Exception as e:
        logger.error(f"Error creating user_folder_mappings table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def initialize_default_permissions():
    """Initialize default folder permissions."""
    db = SessionLocal()
    try:
        logger.info("Initializing default folder permissions...")
        
        # Define default folders and permissions
        default_permissions = [
            {"path": "Organized/Invoices", "role": "staff", "perm": "write"},
            {"path": "Organized/BL", "role": "staff", "perm": "write"},
            {"path": "Organized/NRC", "role": "staff", "perm": "write"},
            {"path": "Organized/FDA", "role": "staff", "perm": "read"},
            {"path": "Organized/Licenses", "role": "staff", "perm": "read"},
            {"path": "Organized/Contracts", "role": "staff", "perm": "read"},
        ]
        
        for folder_def in default_permissions:
            # Check if permission already exists
            existing = db.query(FolderPermission).filter(
                FolderPermission.folder_path == folder_def["path"],
                FolderPermission.role == folder_def["role"]
            ).first()
            
            if not existing:
                perm = FolderPermission(
                    folder_path=folder_def["path"],
                    role=folder_def["role"],
                    permission=folder_def["perm"],
                    created_at=None  # Will be set by DB default
                )
                db.add(perm)
                logger.info(f"  ✓ Created permission: {folder_def['path']} for {folder_def['role']}")
            else:
                logger.info(f"  - Permission already exists: {folder_def['path']} for {folder_def['role']}")
        
        db.commit()
        logger.info("✓ Default permissions initialized")
        
    except Exception as e:
        logger.error(f"Error initializing default permissions: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def run_migration():
    """Run all migration steps."""
    logger.info("=" * 60)
    logger.info("PHASE 2 MIGRATION: 2FA and Folder Permissions")
    logger.info("=" * 60)
    
    try:
        # Step 1: Add 2FA fields to users table
        logger.info("\n[Step 1/4] Migrating 2FA fields...")
        migrate_2fa_fields()
        
        # Step 2: Create folder_permissions table
        logger.info("\n[Step 2/4] Creating folder_permissions table...")
        create_folder_permissions_table()
        
        # Step 3: Create user_folder_mappings table
        logger.info("\n[Step 3/4] Creating user_folder_mappings table...")
        create_user_folder_mappings_table()
        
        # Step 4: Initialize default permissions
        logger.info("\n[Step 4/4] Initializing default permissions...")
        initialize_default_permissions()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ PHASE 2 MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"✗ MIGRATION FAILED: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    run_migration()