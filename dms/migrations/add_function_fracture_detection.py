"""
Database Migration: Add Function and Fracture Detection Fields
This migration adds fields for document function detection and quality analysis
"""
import sqlite3
from pathlib import Path


def migrate():
    """Add function and fracture detection fields to documents table"""
    db_path = Path(__file__).parent.parent / "dms.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('documents')
            WHERE name IN ('function_type', 'quality_level', 'has_damage')
        """)
        row = cursor.fetchone()
        if row and row[0] >= 3:
            print("Migration already applied. Skipping.")
            conn.close()
            return

        # Add new columns
        print("Adding function_type column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN function_type VARCHAR(50)
        """)
        
        print("Adding function_confidence column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN function_confidence FLOAT
        """)
        
        print("Adding quality_level column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN quality_level VARCHAR(20)
        """)
        
        print("Adding has_damage column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN has_damage BOOLEAN DEFAULT 0 NOT NULL
        """)
        
        print("Adding damage_type column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN damage_type VARCHAR(50)
        """)
        
        print("Adding damage_severity column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN damage_severity VARCHAR(20)
        """)
        
        print("Adding quality_analysis_metadata column...")
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN quality_analysis_metadata JSON
        """)
        
        conn.commit()
        conn.close()
        
        print("Migration completed successfully: Function and Fracture Detection fields added")

    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise


if __name__ == "__main__":
    migrate()