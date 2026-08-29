#!/usr/bin/env python3
"""
Migration script to add expiry_date and expiry_notes columns to documents table.
Run this script to update the database schema for Phase 1 upgrade.
"""
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_expiry_columns():
    """Add expiry_date and expiry_notes columns to documents table."""
    
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(documents)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            if 'expiry_date' in existing_columns and 'expiry_notes' in existing_columns:
                logger.info("Expiry columns already exist in documents table. Skipping migration.")
                return True
            
            # Add expiry_date column
            if 'expiry_date' not in existing_columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN expiry_date DATE"))
                conn.commit()
                logger.info("Added expiry_date column to documents table")
            else:
                logger.info("expiry_date column already exists")
            
            # Add expiry_notes column
            if 'expiry_notes' not in existing_columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN expiry_notes TEXT"))
                conn.commit()
                logger.info("Added expiry_notes column to documents table")
            else:
                logger.info("expiry_notes column already exists")
            
            logger.info("Migration completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate_expiry_columns()
    sys.exit(0 if success else 1)
