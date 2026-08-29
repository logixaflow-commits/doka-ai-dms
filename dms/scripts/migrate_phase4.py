"""
Migration Script: Phase 4 - Scalability & Extensibility
This script adds the necessary database changes for Phase 4 upgrade.

Run this script directly: python scripts/migrate_phase4.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.database import Document, DocumentVersion, ExternalAPIProvider, ExternalAPILog, SystemHealthLog
from loguru import logger


def migrate_document_version_fields():
    """Add versioning fields to documents table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        columns = inspector.get_columns('documents')
        column_names = [col['name'] for col in columns]
        
        if 'version' not in column_names:
            logger.info("Adding version column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1"))
            db.commit()
            logger.info("✓ version column added")
        else:
            logger.info("version column already exists")
        
        if 'version_group_id' not in column_names:
            logger.info("Adding version_group_id column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN version_group_id VARCHAR(36)"))
            db.commit()
            logger.info("✓ version_group_id column added")
        else:
            logger.info("version_group_id column already exists")
        
        if 'parent_version_id' not in column_names:
            logger.info("Adding parent_version_id column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN parent_version_id INTEGER"))
            db.commit()
            logger.info("✓ parent_version_id column added")
        else:
            logger.info("parent_version_id column already exists")
        
        if 'version_comment' not in column_names:
            logger.info("Adding version_comment column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN version_comment TEXT"))
            db.commit()
            logger.info("✓ version_comment column added")
        else:
            logger.info("version_comment column already exists")
        
    except Exception as e:
        logger.error(f"Error adding version fields to documents: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_document_versions_table():
    """Create document_versions table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'document_versions' not in tables:
            logger.info("Creating document_versions table...")
            
            db.execute(text("""
                CREATE TABLE document_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    storage_key VARCHAR(500) NOT NULL,
                    file_hash VARCHAR(64) NOT NULL,
                    file_size INTEGER NOT NULL,
                    uploaded_by INTEGER NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    comment TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents(id),
                    FOREIGN KEY (uploaded_by) REFERENCES users(id)
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_document_versions_document_id ON document_versions(document_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_document_versions_document_id ON document_versions(document_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_document_versions_version ON document_versions(version)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_document_versions_version ON document_versions(version)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_doc_version_doc_ver ON document_versions(document_id, version)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_doc_version_doc_ver ON document_versions(document_id, version)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ document_versions table created")
        else:
            logger.info("document_versions table already exists")
        
    except Exception as e:
        logger.error(f"Error creating document_versions table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_external_api_providers_table():
    """Create external_api_providers table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'external_api_providers' not in tables:
            logger.info("Creating external_api_providers table...")
            
            db.execute(text("""
                CREATE TABLE external_api_providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    provider_type VARCHAR(50) NOT NULL,
                    base_url VARCHAR(500) NOT NULL,
                    auth_type VARCHAR(20) NOT NULL,
                    auth_config TEXT NOT NULL,
                    endpoints JSON NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE NOT NULL,
                    webhook_secret VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_external_api_providers_name ON external_api_providers(name)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_external_api_providers_name ON external_api_providers(name)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_external_api_providers_enabled ON external_api_providers(enabled)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_external_api_providers_enabled ON external_api_providers(enabled)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ external_api_providers table created")
        else:
            logger.info("external_api_providers table already exists")
        
    except Exception as e:
        logger.error(f"Error creating external_api_providers table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_external_api_logs_table():
    """Create external_api_logs table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'external_api_logs' not in tables:
            logger.info("Creating external_api_logs table...")
            
            db.execute(text("""
                CREATE TABLE external_api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    document_id INTEGER,
                    endpoint VARCHAR(100) NOT NULL,
                    request TEXT NOT NULL,
                    response TEXT,
                    status_code INTEGER,
                    error TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (provider_id) REFERENCES external_api_providers(id),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_external_api_logs_provider_id ON external_api_logs(provider_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_external_api_logs_provider_id ON external_api_logs(provider_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_external_api_logs_document_id ON external_api_logs(document_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_external_api_logs_document_id ON external_api_logs(document_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_external_api_logs_timestamp ON external_api_logs(timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_external_api_logs_timestamp ON external_api_logs(timestamp)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_api_log_provider_time ON external_api_logs(provider_id, timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_api_log_provider_time ON external_api_logs(provider_id, timestamp)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_api_log_doc_time ON external_api_logs(document_id, timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_api_log_doc_time ON external_api_logs(document_id, timestamp)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ external_api_logs table created")
        else:
            logger.info("external_api_logs table already exists")
        
    except Exception as e:
        logger.error(f"Error creating external_api_logs table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_system_health_logs_table():
    """Create system_health_logs table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'system_health_logs' not in tables:
            logger.info("Creating system_health_logs table...")
            
            db.execute(text("""
                CREATE TABLE system_health_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    metrics JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes with IF NOT EXISTS
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_system_health_logs_service ON system_health_logs(service)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_system_health_logs_service ON system_health_logs(service)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_system_health_logs_timestamp ON system_health_logs(timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_system_health_logs_timestamp ON system_health_logs(timestamp)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_health_log_service_time ON system_health_logs(service, timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_health_log_service_time ON system_health_logs(service, timestamp)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ system_health_logs table created")
        else:
            logger.info("system_health_logs table already exists")
        
    except Exception as e:
        logger.error(f"Error creating system_health_logs table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def setup_version_group_trigger():
    """Setup trigger to auto-generate version_group_id for new documents."""
    db = SessionLocal()
    try:
        logger.info("Setting up version_group_id trigger...")
        
        # Check if we're using PostgreSQL or SQLite
        is_pg = 'postgresql' in str(engine.url).lower()
        
        if is_pg:
            # PostgreSQL trigger
            try:
                db.execute(text("""
                    CREATE OR REPLACE FUNCTION generate_version_group_id()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        IF NEW.version_group_id IS NULL THEN
                            NEW.version_group_id := gen_random_uuid()::text;
                        END IF;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                db.execute(text("""
                    DROP TRIGGER IF EXISTS set_version_group_id ON documents;
                """))
                
                db.execute(text("""
                    CREATE TRIGGER set_version_group_id
                    BEFORE INSERT ON documents
                    FOR EACH ROW
                    EXECUTE FUNCTION generate_version_group_id();
                """))
                
                db.commit()
                logger.info("✓ PostgreSQL version_group_id trigger created")
            except Exception as e:
                logger.warning(f"Failed to create PostgreSQL trigger: {e}")
                logger.warning("Trigger setup skipped (will use application-level fallback)")
        else:
            # SQLite doesn't support triggers, we'll handle this in application code
            logger.info("SQLite detected - skipping trigger (version_group_id will be generated in application code)")
            
    except Exception as e:
        logger.error(f"Error setting up version_group trigger: {e}")
        raise
    finally:
        db.close()


def backfill_version_group_ids():
    """Backfill version_group_id for existing documents."""
    db = SessionLocal()
    try:
        logger.info("Backfilling version_group_id for existing documents...")
        
        # Import uuid for generating IDs
        import uuid
        
        # Get documents without version_group_id
        result = db.execute(text("""
            SELECT id FROM documents WHERE version_group_id IS NULL
        """))
        
        documents = result.fetchall()
        if not documents:
            logger.info("✓ All documents already have version_group_id")
            return
            
        count = 0
        for doc in documents:
            version_group_id = str(uuid.uuid4())
            db.execute(text("""
                UPDATE documents SET version_group_id = :vgid WHERE id = :id
            """), {"vgid": version_group_id, "id": doc[0]})
            count += 1
            
        db.commit()
        logger.info(f"✓ Backfilled version_group_id for {count} documents")
        
    except Exception as e:
        logger.error(f"Error backfilling version_group_ids: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def run_migration():
    """Run all migration steps."""
    logger.info("=" * 60)
    logger.info("PHASE 4 MIGRATION: Scalability & Extensibility")
    logger.info("=" * 60)
    
    try:
        # Step 1: Add version fields to documents table
        logger.info("\n[Step 1/7] Migrating version fields to documents table...")
        migrate_document_version_fields()
        
        # Step 2: Setup version_group_id trigger
        logger.info("\n[Step 2/7] Setting up version_group_id trigger...")
        setup_version_group_trigger()
        
        # Step 3: Backfill version_group_id for existing documents
        logger.info("\n[Step 3/7] Backfilling version_group_id for existing documents...")
        backfill_version_group_ids()
        
        # Step 4: Create document_versions table
        logger.info("\n[Step 4/7] Creating document_versions table...")
        create_document_versions_table()
        
        # Step 5: Create external_api_providers table
        logger.info("\n[Step 5/7] Creating external_api_providers table...")
        create_external_api_providers_table()
        
        # Step 6: Create external_api_logs table
        logger.info("\n[Step 6/7] Creating external_api_logs table...")
        create_external_api_logs_table()
        
        # Step 7: Create system_health_logs table
        logger.info("\n[Step 7/7] Creating system_health_logs table...")
        create_system_health_logs_table()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ PHASE 4 MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"✗ MIGRATION FAILED: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    run_migration()