#!/usr/bin/env python3
"""
Office DMS - Main Entry Point
Handles: database init, seed data, file watcher startup, and Uvicorn server.
"""

import os
import sys
from pathlib import Path

# Ensure app is in path
sys.path.insert(0, str(Path(__file__).parent))


def init_db_and_seed():
    """Initialize database and seed default data."""
    from app.core.database import init_database, SessionLocal
    from app.core.security import hash_password
    from app.core.config import settings
    from app.models.database import User, SOPTemplate
    import yaml

    init_database()

    db = SessionLocal()
    try:
        # Create default admin user if not exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@officedms.local",
                password_hash=hash_password("admin123"),
                full_name="System Administrator",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("[INIT] Default admin user created: admin / admin123")

        # Create system user for file watcher
        system = db.query(User).filter(User.username == "system").first()
        if not system:
            system = User(
                username="system",
                email="system@officedms.local",
                password_hash=hash_password(os.urandom(32).hex()),
                full_name="System Process",
                role="staff",
                is_active=True,
            )
            db.add(system)
            db.commit()
            print("[INIT] System user created")

        # Seed SOP templates from config
        config_path = Path(__file__).parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            sop_defaults = config.get("sop_defaults", {})
            for key, template_data in sop_defaults.items():
                existing = (
                    db.query(SOPTemplate)
                    .filter(SOPTemplate.name == template_data["name"])
                    .first()
                )
                if not existing:
                    sop = SOPTemplate(
                        name=template_data["name"],
                        description=template_data.get("description", ""),
                        document_types=template_data.get("document_types", []),
                        steps=template_data.get("steps", []),
                        is_active=True,
                    )
                    db.add(sop)
                    print(f"[INIT] SOP template created: {template_data['name']}")

            db.commit()

        print("[INIT] Database seeded successfully")

    except Exception as e:
        db.rollback()
        print(f"[INIT] Warning: Seeding error: {e}")
    finally:
        db.close()


def start_watcher():
    """Start the file watcher in background."""
    from app.services.watcher import file_watcher

    file_watcher.start()
    print("[WATCHER] File watcher started")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Office DMS")
    parser.add_argument(
        "--init", action="store_true", help="Initialize database and seed data"
    )
    parser.add_argument("--watcher", action="store_true", help="Start file watcher")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload (dev)"
    )
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    # Always initialize DB
    init_db_and_seed()

    # Start file watcher if requested
    if args.watcher:
        start_watcher()

    # Start server
    import uvicorn

    print(f"[SERVER] Starting Office DMS on {args.host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()
