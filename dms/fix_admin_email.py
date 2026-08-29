"""
Fix admin user email to be valid
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.database import User

def fix_admin_email():
    db = SessionLocal()
    try:
        # Get admin user
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print(f"Current admin email: {admin.email}")
            # Update to a valid email
            admin.email = "admin@example.com"
            db.commit()
            print(f"Updated admin email to: {admin.email}")
        else:
            print("Admin user not found")
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_email()