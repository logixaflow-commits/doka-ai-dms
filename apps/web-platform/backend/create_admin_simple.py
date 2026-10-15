from app.core.database import SessionLocal
import bcrypt
from app.models.database import User

db = SessionLocal()
try:
    # Check if admin exists
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        print('Admin already exists')
    else:
        # Create admin user with direct bcrypt hashing
        password = b"admin123"  # Simple password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password, salt).decode('utf-8')
        
        admin = User(
            username="admin",
            email="admin@officedms.local",
            password_hash=password_hash,
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