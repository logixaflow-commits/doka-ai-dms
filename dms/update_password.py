from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.database import User

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        admin.password_hash = hash_password('admin123')
        db.commit()
        print('Password updated successfully')
    else:
        print('Admin not found')
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()