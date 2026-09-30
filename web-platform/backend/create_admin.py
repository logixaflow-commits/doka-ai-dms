from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.database import User

db = SessionLocal()
try:
    # Check if admin exists
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        print('Admin already exists')
    else:
        # Create admin user
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
        print('Admin user created successfully: admin / admin123')
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()