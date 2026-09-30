# Office DMS - AI Document Management System

> **Enterprise-grade, local-first AI document management system** for logistics, customs clearance, and office workflow automation.


---

## Features

- **File Organization** - Auto-organizes messy files (PDFs, images, Excel, Word)
- **OCR (Optical Character Recognition)** - Extracts text from documents including **Myanmar language**
- **Duplicate Detection** - Exact (SHA-256) + near-duplicate (TF-IDF cosine similarity)
- **AI Classification** - Keyword matching + TF-IDF fallback (Invoice, BL, NRC, FDA, etc.)
- **Folder Suggestions** - Smart folder structure recommendations
- **SOP Tracking** - Standard Operating Procedure progress tracking
- **ETA/Follow-up Reminders** - Automated deadline reminders
- **Human Approval** - No auto-move; all actions require human approval
- **Audit Trail** - Every action logged with user, timestamp, IP
- **Role-Based Access** - Admin, Staff, Customer roles
- **Encryption** - Fernet AES encryption for sensitive documents
- **Local-First** - Zero cloud dependency; runs entirely on-premise

---

## Quick Start

### Option 1: Docker (Recommended for Production)

```bash
# Clone and enter directory
cd web-platform/backend/

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Access the application
open http://localhost:8000
# Default login: admin / admin123
```

### Option 2: Local Python (Development)

**Prerequisites:**

- Python 3.11+
- Tesseract OCR with Myanmar language pack
- PostgreSQL 15+ (or SQLite for dev)
- Redis 7+
- MinIO (optional, falls back to filesystem)

```bash
# Install Tesseract (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-mya

# macOS
brew install tesseract tesseract-lang

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

cd web-platform/backend/

# Setup environment
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, etc.

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run
./run.sh        # Linux/macOS
run.bat         # Windows

# Or directly
python run.py --host 0.0.0.0 --port 8000 --reload
```

---

## Default Login

| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin123` | Admin |

> **IMPORTANT:** Change the default admin password immediately after first login!

---

## Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | dev / production | `development` |
| `SECRET_KEY` | JWT signing key | (generate new) |
| `ENCRYPTION_KEY` | Fernet encryption key | (generate new) |
| `DATABASE_URL` | PostgreSQL or SQLite | SQLite |
| `REDIS_URL` | Redis broker URL | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | MinIO/S3 endpoint | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |
| `TESSERACT_CMD` | Tesseract binary path | `tesseract` |

### config.yaml

Edit `config.yaml` to customize:
- **Suppliers** - Add your suppliers with aliases
- **Keywords** - Customize document classification keywords
- **Regex Patterns** - Add custom metadata extraction patterns
- **SOP Templates** - Define standard operating procedures
- **Thresholds** - Adjust confidence thresholds

---

## Folder Structure

```
Office_DMS/
├── Original_Files/       # READ-ONLY: Original files never touched
├── Watch_Folder/         # Drop files here for auto-processing
├── Processing_Workspace/ # Temporary copies for AI (auto-cleaned daily)
├── Organized/            # AI-suggested organized structure
│   ├── Import/
│   ├── Export/
│   ├── NRC/
│   ├── FDA/
│   ├── Invoices/
│   ├── BL/
│   └── ...
├── Duplicate/            # Duplicate files (after approval)
├── Suspicious/           # Files flagged by metadata anomalies
└── backups/              # Automated database backups
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with username/password |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/register` | Register new user (admin only) |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents` | List documents (paginated) |
| GET | `/api/documents/pending` | List pending review |
| GET | `/api/documents/{id}` | Get document details |
| POST | `/api/documents/{id}/approve` | Approve document |
| POST | `/api/documents/{id}/reject` | Reject document |
| POST | `/api/documents/upload` | Upload new document |
| GET | `/api/documents/{id}/preview` | Get presigned URL |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=keyword` | Full-text search |

### SOP
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sop/templates` | List SOP templates |
| POST | `/api/sop/instances` | Create SOP instance |
| POST | `/api/sop/instances/{id}/advance` | Advance step |

### Reminders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reminders` | List reminders |
| POST | `/api/reminders/{id}/dismiss` | Dismiss reminder |

### Audit (Admin Only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/audit/logs` | View audit trail |
| GET | `/api/admin/stats` | System statistics |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/config` | Public configuration |

---

## Architecture

### 6-Layer Architecture

```
Layer 1: File Ingestion & Watcher    (watchdog → Celery)
Layer 2: Async Task Queue            (Celery + Redis)
Layer 3: Secure Object Storage       (MinIO / S3)
Layer 4: AI Processing Pipeline      (OCR → Metadata → Classify → Duplicate → Folder)
Layer 5: Web Application             (FastAPI + Jinja2 + React)
Layer 6: Security & Monitoring       (RBAC + Encryption + Audit + Logging)
```

### AI Pipeline (6 Steps)

1. **OCR Extraction** - Tesseract + pdf2image (Myanmar supported)
2. **Metadata Extraction** - Regex patterns (NRC, Invoice, ETA, Supplier, BL)
3. **Classification** - Keyword matching + TF-IDF fallback
4. **Duplicate Detection** - SHA-256 (exact) + TF-IDF cosine similarity (near)
5. **Folder Suggestion** - Based on category + supplier
6. **Database Insert** - Status = pending (awaiting human approval)

---

## Security

- **Never modify original files** - AI works only on copies
- **Human approval required** - No auto-delete or auto-move
- **Role-based access control** - Admin / Staff / Customer
- **Encryption at rest** - Fernet AES for sensitive documents (NRC, Customs, Invoices)
- **Audit logging** - Every action logged with user_id, action, timestamp, IP
- **Presigned URLs** - Time-limited secure file access
- **Password hashing** - bcrypt with 12 rounds
- **JWT tokens** - Access + refresh tokens with expiry
- **Rate limiting** - Login attempt lockout after 5 failures

---

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Web App | dms_fastapi | 8000 | FastAPI + Uvicorn |
| Celery Worker | dms_celery_worker | - | Background task processing |
| Celery Beat | dms_celery_beat | - | Scheduled tasks |
| Redis | dms_redis | 6379 | Message broker |
| PostgreSQL | dms_postgres | 5432 | Primary database |
| MinIO | dms_minio | 9000, 9001 | Object storage |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_security.py -v
pytest tests/test_classifier.py -v
```

---

## Troubleshooting

### Tesseract / OCR Issues
```bash
# Check Tesseract installation
tesseract --version
tesseract --list-langs  # Should include 'mya'

# Install Myanmar language pack
sudo apt-get install tesseract-ocr-mya
```

### Database Connection
```bash
# Check PostgreSQL
pg_isready -h localhost -p 5432

# Use SQLite for development
# Edit .env: DATABASE_URL=sqlite:///./Office_DMS/database/dms.db
```

### Redis Connection
```bash
# Check Redis
redis-cli ping  # Should return PONG
```

### Celery Tasks Not Processing
```bash
# Check Celery worker logs
docker logs dms_celery_worker

# Restart Celery
docker-compose -f infrastructure/docker/docker-compose.yml restart celery_worker celery_beat
```

---

## License

This project is proprietary software for internal use.

## Support

For issues and questions, contact the Office DMS development team.
