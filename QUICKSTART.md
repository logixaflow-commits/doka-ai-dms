# 🚀 Enterprise AI DMS - Quick Start Guide

Get your Enterprise AI Document Management System running in **5 minutes**.

---

## ⚡ Fastest Start (Docker)

```bash
# 1. Navigate to the project directory
cd "D:\1 main\Enterprise AI DMS Blueprint"

# 2. Start all services
docker-compose up -d

# 3. Check services are running
docker-compose ps

# 4. Access the system
# Open browser: http://localhost:8000
# Login: admin / admin123

# That's it! You're running.
```

---

## 📋 Detailed Quick Start

### Step 1: Verify Prerequisites

**For Docker:**
```bash
docker --version    # Should be 20.10+
docker-compose --version    # Should be 2.0+
```

**For Local Installation:**
```bash
python --version    # Should be 3.11+
tesseract --version    # Should have Myanmar (mya) language
```

### Step 2: Configure Environment

**Docker (Default config works):**
- Default configuration in `docker-compose.yml` is sufficient for development
- No changes needed for initial testing

**Local Installation:**
```bash
# Copy environment template
cd dms
cp .env.example .env

# Edit .env if needed (defaults work for development)
# Key settings:
# - DATABASE_URL: sqlite:///./dms.db (default)
# - REDIS_URL: redis://localhost:6379/0
# - TESSERACT_CMD: Path to tesseract executable
```

### Step 3: Start the System

**Option A: Docker (Recommended)**
```bash
cd "D:\1 main\Enterprise AI DMS Blueprint"
docker-compose up -d
```

**Option B: Startup Scripts**
```bash
# Linux/Mac
./run.sh

# Windows
run.bat
```

**Option C: Manual (Advanced)**
```bash
# Terminal 1: Web Application
cd dms
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload --factory

# Terminal 2: Celery Worker
cd dms
celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Celery Beat
cd dms
celery -A app.core.celery_app beat --loglevel=info
```

### Step 4: Initialize System

**With Docker:**
```bash
# Initialize MinIO (creates buckets)
docker-compose exec web python scripts/init_minio.py

# Create admin user (if not exists)
docker-compose exec web python create_admin.py
```

**Local:**
```bash
cd dms

# Initialize database
python -c "from app.core.database import init_database; init_database()"

# Initialize MinIO
python ../scripts/init_minio.py

# Create admin user
python create_admin.py
```

### Step 5: Access the System

Open your browser and navigate to:
- **Web Interface:** http://localhost:8000
- **API Documentation:** http://localhost:8000/api/docs
- **MinIO Console:** http://localhost:9001

**Login Credentials:**
- Username: `admin`
- Password: `admin123`

---

## 🎯 First Steps After Login

### 1. Upload a Test Document
- Navigate to Dashboard
- Click "Upload Document"
- Select a PDF file
- Watch it process (OCR + Classification)

### 2. Test Myanmar Search
- Navigate to Search
- Type Myanmar text: "ခင်ဗျား"
- See results appear instantly

### 3. Try Bulk Actions
- Navigate to Pending Documents
- Select multiple documents
- Click "Bulk Approve"
- Watch them auto-rename

### 4. Test Document Locking
- Navigate to a Document Detail
- Click "Lock Document"
- Open the same document in another tab
- See lock conflict detection

### 5. Watch Real-time Updates
- Stay on Dashboard
- Upload a new document
- Watch stats update automatically (no refresh needed)

---

## 🐳 Docker Services Overview

When you run `docker-compose up -d`, you get:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Task Queue |
| MinIO | 9000 | File Storage |
| MinIO Console | 9001 | Storage Management |
| Web Application | 8000 | Main Application |
| Celery Worker | - | Background Tasks |
| Celery Beat | - | Scheduled Tasks |

---

## 🔧 Common Issues & Solutions

### Issue: "Tesseract not found"
**Solution:**
```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-mya

# Mac
brew install tesseract tesseract-lang

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Issue: "Database connection failed"
**Solution:**
```bash
# For Docker: Check PostgreSQL is healthy
docker-compose ps postgres

# For Local: Ensure SQLite file exists
# Edit .env: DATABASE_URL=sqlite:///./dms.db
```

### Issue: "Redis connection refused"
**Solution:**
```bash
# Start Redis
redis-server

# Or with Docker
docker-compose up redis
```

### Issue: "MinIO connection failed"
**Solution:**
```bash
# Initialize MinIO
python scripts/init_minio.py

# Or with Docker
docker-compose exec web python scripts/init_minio.py
```

### Issue: "Celery tasks not executing"
**Solution:**
```bash
# Check Celery worker is running
docker-compose ps celery-worker

# Check logs
docker-compose logs celery-worker
```

---

## 📊 Verify System Health

After starting, verify everything works:

```bash
# Check all services are running
docker-compose ps

# Check web application health
curl http://localhost:8000/api/health

# Check API documentation
curl http://localhost:8000/api/docs

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

## 🎨 Frontend Features to Try

1. **Dashboard** - Real-time stats, bulk actions
2. **Pending Documents** - Pagination, bulk approve/reject
3. **Document Detail** - PDF preview, locking, approve/reject
4. **Search** - Myanmar FTS, advanced filters
5. **SOP Tracker** - Standard Operating Procedures
6. **Reminders** - ETA alerts, notifications
7. **Audit Log** - Complete activity trail (admin)

---

## 🔐 Security Configuration

For production, update these in `dms/.env`:

```env
# Change these in production!
SECRET_KEY=your-super-secret-32-char-key
ENCRYPTION_KEY=your-fernet-encryption-key

# Configure SMTP for email alerts
SMTP_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Configure OpenAI for enhanced duplicate detection
OPENAI_API_KEY=your-openai-api-key
AI_ENHANCED_DUPLICATE_DETECTION=true
```

---

## 📚 Documentation Links

- [Complete Documentation](README.md)
- [Backend API Documentation](BACKEND_DOCUMENTATION.md)
- [Frontend Documentation](FRONTEND_DOCUMENTATION.md)
- [Complete System Documentation](ENTERPRISE_DMS_COMPLETE.md)
- [Verification Checklist](VERIFICATION.md)
- [Complete Codebase Summary](COMPLETE_CODEBASE.md)

---

## 🎉 You're Running!

**What you can do now:**
- ✅ Upload and process documents
- ✅ Search with Myanmar text
- ✅ Bulk approve/reject
- ✅ Auto-rename documents
- ✅ Lock documents to prevent conflicts
- ✅ Watch real-time updates
- ✅ Export reports
- ✅ Manage SOPs and reminders

**Next Steps:**
1. Configure SMTP for email alerts
2. Configure OpenAI for enhanced detection
3. Set up automated backups
4. Configure production database (PostgreSQL)
5. Set up monitoring and logging
6. Deploy to production server

---

**Need Help?**
- Check the documentation files
- Review logs in `logs/` directory
- Check API docs at `/api/docs`
- Review troubleshooting section

**Happy Document Managing! 🚀**

---

**Version:** 1.0.0
**Last Updated:** 2026-06-21
**Status:** Ready to Run