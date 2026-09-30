"""
Office DMS - Database Migration Script for Social Media Features
Adds source, source_metadata, daily_folder, and is_daily_archived columns to documents table.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.database import SessionLocal, engine
from sqlalchemy import text
from app.core.logging import get_logger

logger = get_logger(__name__)


def migrate_database():
    """
    Perform database migration to add social media fields.
    
    This script adds the following columns to the documents table:
    - source (VARCHAR(50), nullable, indexed)
    - source_metadata (JSON, nullable)
    - daily_folder (VARCHAR(100), nullable)
    - is_daily_archived (BOOLEAN, default FALSE, not nullable)
    """
    db = SessionLocal()
    
    try:
        # Check if columns already exist
        inspector = engine.dialect.get_inspector(engine)
        columns = inspector.get_columns('documents')
        existing_columns = [col['name'] for col in columns]
        
        logger.info(f"Existing columns: {existing_columns}")
        
        # Add source column if it doesn't exist
        if 'source' not in existing_columns:
            logger.info("Adding 'source' column...")
            db.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN source VARCHAR(50) NULL
            """))
            db.execute(text("""
                CREATE INDEX idx_documents_source ON documents(source)
            """))
            logger.info("✓ 'source' column added")
        else:
            logger.info("'source' column already exists")
        
        # Add source_metadata column if it doesn't exist
        if 'source_metadata' not in existing_columns:
            logger.info("Adding 'source_metadata' column...")
            db.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN source_metadata JSON NULL
            """))
            logger.info("✓ 'source_metadata' column added")
        else:
            logger.info("'source_metadata' column already exists")
        
        # Add daily_folder column if it doesn't exist
        if 'daily_folder' not in existing_columns:
            logger.info("Adding 'daily_folder' column...")
            db.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN daily_folder VARCHAR(100) NULL
            """))
            logger.info("✓ 'daily_folder' column added")
        else:
            logger.info("'daily_folder' column already exists")
        
        # Add is_daily_archived column if it doesn't exist
        if 'is_daily_archived' not in existing_columns:
            logger.info("Adding 'is_daily_archived' column...")
            db.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN is_daily_archived BOOLEAN NOT NULL DEFAULT FALSE
            """))
            logger.info("✓ 'is_daily_archived' column added")
        else:
            logger.info("'is_daily_archived' column already exists")
        
        # Commit changes
        db.commit()
        logger.info("✓ Database migration completed successfully")
        
        # Show final schema
        logger.info("\nFinal documents table schema:")
        columns = inspector.get_columns('documents')
        for col in columns:
            logger.info(f"  {col['name']}: {col['type']} {'NOT NULL' if not col['nullable'] else 'NULL'}")
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Database migration failed: {e}")
        return False
    finally:
        db.close()


def verify_migration():
    """
    Verify that the migration was successful.
    """
    db = SessionLocal()
    
    try:
        # Check if new columns exist
        inspector = engine.dialect.get_inspector(engine)
        columns = inspector.get_columns('documents')
        existing_columns = [col['name'] for col in columns]
        
        required_columns = ['source', 'source_metadata', 'daily_folder', 'is_daily_archived']
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return False
        else:
            logger.info("✓ All required columns present")
            return True
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
    finally:
        db.close()


def rollback_migration():
    """
    Rollback the database migration by removing the new columns.
    WARNING: This will delete any data in the new columns.
    """
    db = SessionLocal()
    
    try:
        logger.warning("⚠ ROLLING BACK DATABASE MIGRATION")
        logger.warning("This will delete the new columns and any data in them!")
        
        confirm = input("Are you sure you want to rollback? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("Rollback cancelled")
            return
        
        # Drop columns
        columns_to_drop = ['source', 'source_metadata', 'daily_folder', 'is_daily_archived']
        
        for column in columns_to_drop:
            try:
                logger.info(f"Dropping column '{column}'...")
                db.execute(text(f"ALTER TABLE documents DROP COLUMN IF EXISTS {column}"))
                logger.info(f"✓ Dropped '{column}'")
            except Exception as e:
                logger.warning(f"Failed to drop '{column}': {e}")
        
        # Drop index
        try:
            db.execute(text("DROP INDEX IF EXISTS idx_documents_source"))
            logger.info("✓ Dropped index 'idx_documents_source'")
        except Exception as e:
            logger.warning(f"Failed to drop index: {e}")
        
        db.commit()
        logger.info("✓ Rollback completed successfully")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Rollback failed: {e}")
        return False
    finally:
        db.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration for social media features')
    parser.add_argument('--verify', action='store_true', help='Verify migration was successful')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_migration()
        sys.exit(0 if success else 1)
    elif args.rollback:
        success = rollback_migration()
        sys.exit(0 if success else 1)
    else:
        success = migrate_database()
        if success:
            # Automatically verify after migration
            verify_migration()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()