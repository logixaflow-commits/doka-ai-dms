# Doka Backend — Personal Local Edition

The supported backend here is the Doka Personal Local FastAPI application. Follow the repository [QUICKSTART](../../QUICKSTART.md) and [Personal Local runbook](../../docs/PERSONAL_LOCAL_RUNBOOK.md); this file is not a separate setup path.

Use Python 3.12, an isolated `web-platform/backend/.venv`, and `requirements-local.txt`. For tests, lint/build, and smoke checks see [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md). No PostgreSQL, Redis, MinIO, Supabase, or default account is required for local development. Set a private `BOOTSTRAP_ADMIN_PASSWORD` in your untracked `.env` before signing in.

The remainder of this README describes retained Enterprise code and is historical reference only. Its old API, Docker, environment, and storage instructions do not describe or start the active Personal Local product.

## Legacy Enterprise features (not part of Personal Local)

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

## Supported local setup

From the repository root, use `start_application.bat` on Windows or `./run.sh` on macOS/Linux. These launchers use the local Python profile, require Node.js 24.x, bind the services to loopback, and never start the deferred Enterprise Docker stack.

For a manual backend test setup, create `web-platform/backend/.venv` with Python 3.12, install `web-platform/backend/requirements-local.txt` into that environment, then follow the commands in [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md). Do not use `requirements-dev.txt` for Personal Local; it is the legacy Enterprise profile.

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
