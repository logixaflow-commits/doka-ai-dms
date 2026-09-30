"""
Migration Script: Phase 3 - AI & Workflow Automation
This script adds the necessary database changes for Phase 3 upgrade.

Run this script directly: python scripts/migrate_phase3.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base
from app.models.database import Document, AutomationRule, RuleExecutionLog
from loguru import logger


def is_postgresql():
    """Check if using PostgreSQL database."""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT current_database()"))
        db.close()
        return True
    except Exception:
        return False


def migrate_document_ai_fields():
    """Add AI tagging and vector search fields to documents table."""
    db = SessionLocal()
    try:
        # Check if columns exist
        inspector = engine.dialect.get_inspector(engine)
        columns = inspector.get_columns('documents')
        column_names = [col['name'] for col in columns]
        
        if 'tags' not in column_names:
            logger.info("Adding tags column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN tags JSON"))
            db.commit()
            logger.info("✓ tags column added")
        else:
            logger.info("tags column already exists")
        
        if 'embedding' not in column_names:
            logger.info("Adding embedding column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN embedding JSON"))
            db.commit()
            logger.info("✓ embedding column added")
        else:
            logger.info("embedding column already exists")
        
        if 'urgency' not in column_names:
            logger.info("Adding urgency column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN urgency VARCHAR(20)"))
            db.commit()
            logger.info("✓ urgency column added")
        else:
            logger.info("urgency column already exists")
        
        if 'customs_code' not in column_names:
            logger.info("Adding customs_code column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN customs_code VARCHAR(20)"))
            db.commit()
            logger.info("✓ customs_code column added")
        else:
            logger.info("customs_code column already exists")
        
    except Exception as e:
        logger.error(f"Error adding AI fields to documents: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_automation_rules_table():
    """Create automation_rules table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'automation_rules' not in tables:
            logger.info("Creating automation_rules table...")
            
            db.execute(text("""
                CREATE TABLE automation_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    condition JSON NOT NULL,
                    actions JSON NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE NOT NULL,
                    priority INTEGER DEFAULT 0,
                    logic VARCHAR(10) DEFAULT 'AND',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    last_triggered TIMESTAMP
                )
            """))
            db.commit()
            
            # Create indexes with IF NOT EXISTS (for PostgreSQL compatibility)
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_automation_rules_name ON automation_rules(name)"))
            except Exception:
                # SQLite doesn't support IF NOT EXISTS for indexes
                try:
                    db.execute(text("CREATE INDEX ix_automation_rules_name ON automation_rules(name)"))
                except Exception:
                    pass  # Index already exists
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_automation_rules_enabled ON automation_rules(enabled)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_automation_rules_enabled ON automation_rules(enabled)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_automation_rules_priority ON automation_rules(priority)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_automation_rules_priority ON automation_rules(priority)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ automation_rules table created")
        else:
            logger.info("automation_rules table already exists")
        
    except Exception as e:
        logger.error(f"Error creating automation_rules table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_rule_execution_logs_table():
    """Create rule_execution_logs table."""
    db = SessionLocal()
    try:
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        if 'rule_execution_logs' not in tables:
            logger.info("Creating rule_execution_logs table...")
            
            db.execute(text("""
                CREATE TABLE rule_execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    document_id INTEGER,
                    executed BOOLEAN,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES automation_rules(id),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """))
            db.commit()
            
            # Create indexes with IF NOT EXISTS (for PostgreSQL compatibility)
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_rule_logs_rule_id ON rule_execution_logs(rule_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_rule_logs_rule_id ON rule_execution_logs(rule_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_rule_logs_doc_id ON rule_execution_logs(document_id)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_rule_logs_doc_id ON rule_execution_logs(document_id)"))
                except Exception:
                    pass
                    
            try:
                db.execute(text("CREATE INDEX IF NOT EXISTS ix_rule_logs_timestamp ON rule_execution_logs(timestamp)"))
            except Exception:
                try:
                    db.execute(text("CREATE INDEX ix_rule_logs_timestamp ON rule_execution_logs(timestamp)"))
                except Exception:
                    pass
                    
            db.commit()
            
            logger.info("✓ rule_execution_logs table created")
        else:
            logger.info("rule_execution_logs table already exists")
        
    except Exception as e:
        logger.error(f"Error creating rule_execution_logs table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_default_rules():
    """Seed default automation rules from config.yaml."""
    db = SessionLocal()
    try:
        logger.info("Seeding default automation rules...")
        
        # Define default rules
        default_rules = [
            {
                "name": "Auto-Tag Finance Documents",
                "description": "Automatically tag documents related to finance as 'Finance'",
                "condition": [{"field": "category", "operator": "eq", "value": "Invoices"}],
                "actions": [{"action_type": "set_tag", "parameters": {"tag": "Finance"}}],
                "enabled": True,
                "priority": 10,
                "logic": "AND"
            },
            {
                "name": "Flag Urgent Customs Documents",
                "description": "Automatically flag documents with urgency keywords as urgent",
                "condition": [{"field": "category", "operator": "contains", "value": "customs"}],
                "actions": [
                    {"action_type": "set_urgency", "parameters": {"urgency": "urgent"}},
                    {"action_type": "create_reminder", "parameters": {"days": 3, "message": "Follow up on this customs document"}}
                ],
                "enabled": True,
                "priority": 20,
                "logic": "AND"
            },
            {
                "name": "Auto-Folder BL Documents",
                "description": "Automatically set suggested folder for Bill of Lading documents",
                "condition": [{"field": "category", "operator": "eq", "value": "BL"}],
                "actions": [{"action_type": "set_folder", "parameters": {"target_folder": "Organized/BL"}}],
                "enabled": True,
                "priority": 5,
                "logic": "AND"
            }
        ]
        
        seeded_count = 0
        for rule_data in default_rules:
            # Check if rule already exists
            existing = db.query(AutomationRule).filter(
                AutomationRule.name == rule_data["name"]
            ).first()
            
            if not existing:
                rule = AutomationRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    condition=rule_data["condition"],
                    actions=rule_data["actions"],
                    enabled=rule_data["enabled"],
                    priority=rule_data["priority"],
                    logic=rule_data["logic"],
                    created_at=None,  # Will be set by DB default
                    created_by=None  # System-generated
                )
                db.add(rule)
                seeded_count += 1
                logger.info(f"  ✓ Created rule: {rule_data['name']}")
            else:
                logger.info(f"  - Rule already exists: {rule_data['name']}")
        
        db.commit()
        logger.info(f"✓ Seeded {seeded_count} default automation rules")
        
    except Exception as e:
        logger.error(f"Failed to seed default rules: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def setup_pgvector_extension():
    """Setup pgvector extension for PostgreSQL if applicable."""
    if not is_postgresql():
        logger.info("PostgreSQL not detected - skipping pgvector extension (SQLite mode)")
        return
    
    db = SessionLocal()
    try:
        logger.info("PostgreSQL detected - checking pgvector extension...")
        
        # Check if extension already exists
        result = db.execute(text("""
            SELECT 1 FROM pg_extension WHERE extname = 'vector'
        """))
        
        if result.fetchone():
            logger.info("✓ pgvector extension already installed")
        else:
            logger.info("Installing pgvector extension...")
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.commit()
            logger.info("✓ pgvector extension installed successfully")
            
    except Exception as e:
        logger.warning(f"Failed to setup pgvector extension: {e}")
        logger.warning("Continuing migration without pgvector (vector search will be disabled)")
    finally:
        db.close()


def run_migration():
    """Run all migration steps."""
    logger.info("=" * 60)
    logger.info("PHASE 3 MIGRATION: AI & Workflow Automation")
    logger.info("=" * 60)
    
    try:
        # Step 0: Setup pgvector extension (PostgreSQL only)
        logger.info("\n[Step 0/4] Setting up pgvector extension...")
        setup_pgvector_extension()
        
        # Step 1: Add AI fields to documents table
        logger.info("\n[Step 1/4] Migrating AI fields to documents table...")
        migrate_document_ai_fields()
        
        # Step 2: Create automation_rules table
        logger.info("\n[Step 2/4] Creating automation_rules table...")
        create_automation_rules_table()
        
        # Step 3: Create rule_execution_logs table
        logger.info("\n[Step 3/4] Creating rule_execution_logs table...")
        create_rule_execution_logs_table()
        
        # Step 4: Seed default rules
        logger.info("\n[Step 4/4] Seeding default automation rules...")
        seed_default_rules()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ PHASE 3 MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"✗ MIGRATION FAILED: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    run_migration()