# Enterprise AI Document Management System

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Personal Local Runbook](#personal-local-runbook)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Mobile Application](#mobile-application)
- [Monitoring](#monitoring)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Enterprise AI Document Management System (DMS) is being developed first as a safe, single-user local document organizer and DMS for real office testing. The initial workflow protects original source data, works on a verified copy, analyzes Myanmar/English documents, and requires human approval before organization changes are applied. Cloud, multi-user, enterprise integrations, and AI-heavy features are intentionally deferred until the personal edition is stable.

### Current Personal Edition Capabilities
- **Read-only source protection**: Original source folders are never modified by organization.
- **Verified working copy**: Recursive import with SHA-256 verification and resumable sessions.
- **Myanmar + English document understanding**: Local text extraction, OCR, PDF/image handling, DOCX, and XLSX/XLSM extraction.
- **Duplicate/version review**: Exact duplicates and likely version families are surfaced for human review.
- **Safe organization**: Category/folder/filename proposals require explicit approval and copy into Final without overwriting different files.
- **Recovery**: Organization audit journal, safe undo, workspace backups, SHA-256 verification, and recovery-only restore.
- **Local search and preview**: Search the verified working copy and preview/download individual files.
- **Optional AI**: Disabled by default; configurable free-first provider fallback when explicitly enabled.
- **Browser UI**: React/Vite Safe Workspace interface for the local data plane.

The repository also contains legacy/enterprise modules (RBAC, realtime, mobile, integrations, reporting, workflow automation, cloud infrastructure, and advanced AI). They are retained for later phases and are not the current personal-edition readiness boundary.

## 🛡️ Personal Local Mode (Current Priority)

The current development priority is a safe local workflow:

`Original D: drive (read-only) → verified working copy → scan → OCR/content analysis → duplicate/version review → user approval → organized working library`

Core organization must work without paid AI services. AI is optional and uses a configurable free-first provider fallback chain when enabled. The application should never permanently delete or overwrite the original source as part of organization.

## 🌐 Web Access + Local Data (Current Direction)

The application is local-first, but it is also web-accessible. The home/office PC keeps the original files, working copy, database, OCR data, and backups locally. The React/Vite web interface is used from a browser for search, review, viewing, and downloads.

For remote access from the office, the personal setup should use a private VPN/secure tunnel rather than exposing the DMS directly to the public Internet. Local storage is not being removed; web access is an interface over the local data plane.

## 📘 Personal Local Runbook

See `docs/PERSONAL_LOCAL_RUNBOOK.md` for the safe import, review, organization, backup/recovery, OCR, AI, and private-network operating workflow.

## ✨ Features

### Core Features
- User authentication and authorization (JWT, 2FA)
- Document upload and management
- AI-powered document classification
- Function detection (15 document types)
- Fracture/quality detection (8 quality levels)
- Duplicate detection
- Database management (PostgreSQL)
- Security hardening
- Performance optimization
- Email notifications (SMTP)
- Docker deployment
- Production configuration
- Role-based access control (RBAC)
- Audit logging
- Document locking
- Folder permissions
- SOP tracking
- ETA/follow-up reminders
- Advanced search
- Bulk operations
- Document expiry tracking
- Social media ingestion

### Advanced AI Features
- Myanmar Language OCR Support
- Document Preview & Annotation
- Advanced Search with Semantic Search
- Function Detection Service
- Fracture Detection Service
- AI-enhanced analysis

### Real-time Features
- Server-Sent Events (SSE) implementation
- Real-time document status updates
- User activity tracking
- Collaborative editing notifications
- System notifications
- Connection management
- Event broadcasting

### Versioning Features
- Document version history tracking
- Version creation with metadata
- Version comparison (metadata diff)
- Rollback to previous versions
- Version comments and changelog
- File hash calculation
- Version storage management

### Workflow Features
- Custom approval workflow engine
- Conditional routing based on document type
- Automated task assignments
- Workflow templates and definitions
- Workflow triggers and actions
- Workflow monitoring and reporting
- Workflow state machine implementation

### Reporting Features
- Custom report builder engine
- Export to CSV, JSON, Excel
- Scheduled report generation
- Dashboard analytics and visualization
- Report templates
- Data aggregation and analysis
- Document, user, and activity reports

### Rate Limiting Features
- User-based rate limiting
- API usage tracking
- Quota management system
- Rate limit endpoints
- Usage analytics
- Per-minute, per-hour, per-day limits
- Role-based rate limits

### Testing Features
- Unit tests for services
- Integration tests for API endpoints
- E2E tests for workflows
- Test fixtures and mocks
- Coverage reporting
- Test configuration
- CI/CD ready

### Analytics Features
- Prometheus metrics collection
- Custom application metrics
- System performance metrics
- Business intelligence metrics
- Grafana dashboards
- Real-time monitoring
- Alerting support

### Integration Features
- ERP system integrations (SAP, Oracle, Dynamics)
- CRM system integrations (Salesforce, HubSpot, Dynamics 365)
- Accounting system integrations (QuickBooks, Xero, Sage)
- Webhook integrations
- Custom integrations
- Document synchronization
- Integration management

### Mobile Features
- React Native mobile app
- JWT authentication
- Document management
- Document upload
- Search functionality
- User profile
- Offline support
- Push notifications ready
- Biometric authentication ready
- Camera integration

## 🏗️ Architecture

### Technology Stack

#### Backend
- **Framework**: FastAPI
- **Database**: SQLite (development), PostgreSQL (production)
- **Cache**: Redis
- **Storage**: MinIO
- **Task Queue**: Celery
- **OCR**: Tesseract with Myanmar language support
- **AI**: Gemini, Hugging Face, OpenRouter, Groq

#### Frontend
- **Framework**: React + TypeScript
- **UI Components**: Shadcn/ui
- **State Management**: React hooks
- **Styling**: Tailwind CSS

#### Mobile
- **Framework**: React Native with Expo
- **Navigation**: React Navigation
- **UI Components**: React Native Paper
- **Storage**: Expo SecureStore

#### Infrastructure
- **Containerization**: Docker
- **Reverse Proxy**: Nginx
- **Deployment**: Docker Compose
- **Monitoring**: Prometheus + Grafana
- **Logging**: Loguru

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              API Gateway (FastAPI)                      │
├─────────────────────────────────────────────────────────┤
│  • Authentication    • Rate Limiting                    │
│  • Security          • Request Routing                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Application Services                        │
├─────────────────────────────────────────────────────────┤
│  • Document Processing  • AI Services                    │
│  • OCR Processing       • Workflow Engine                 │
│  • Versioning           • Reporting                       │
│  • Analytics            • Integrations                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Data Layer                                 │
├─────────────────────────────────────────────────────────┤
│  • PostgreSQL  • Redis  • MinIO  • Celery               │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Current Local Setup Boundary

The personal edition is intentionally local-first. The original source drive is read-only, and the application writes only to the configured working area.

### Current flow

```
Original source drive (read-only)
        ↓
Verified import / copy session
        ↓
Working Copy
        ↓
Inventory + SHA-256
        ↓
OCR / local text extraction
        ↓
Duplicate + version analysis
        ↓
Review / approval
        ↓
Safe copy to Final
        ↓
Backup + audit history
```

### Current deployment boundary

- **Backend + document data:** local/home machine.
- **Frontend:** React/Vite, usable locally and deployable to Vercel later.
- **Office access:** private VPN/tunnel (recommended: Tailscale), not public port forwarding.
- **Storage:** local filesystem + SQLite for the personal edition.
- **AI:** optional and disabled by default.
- **Sentry:** optional; telemetry is scrubbed to avoid document content/OCR/sensitive paths.
- **Render / Supabase:** reserved for the later cloud/multi-user edition; they are not required for personal local operation.

### What is deliberately deferred

Existing enterprise capabilities remain in the repository, but are not part of the current personal-core workflow: mobile, advanced RBAC/multi-user, external integrations, cloud storage, distributed workers, advanced reporting/realtime, and AI-heavy automation.

## 🗃️ Legacy / Enterprise Reference Setup

### Prerequisites
- Python 3.14+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis 7+
- MinIO

### Backend Installation

```bash
# Clone repository
git clone <repository-url>
cd Enterprise-AI-DMS-Blueprint

# Navigate to backend
cd web-platform/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install test dependencies
pip install -r requirements-test.txt

# Copy environment file
cp .env.example .env

# Update environment variables
# Edit .env with your configuration

# Initialize database
python -c "from app.core.database import init_database; init_database()"

# Run migrations (if using Alembic)
alembic upgrade head
```

### Frontend Installation

```bash
# Navigate to frontend
cd web-platform/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Update environment variables
# Edit .env.local with your configuration

# Start development server
npm run dev
```

### Mobile Application Installation

```bash
# Navigate to mobile
cd mobile

# Install dependencies
npm install

# Start development server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android
```

## ⚙️ Configuration

> The sections below are retained as legacy/enterprise reference material. They are **not** required for the current personal-local workflow. Do not use the example credentials below as real secrets.

### Environment Variables

#### Backend (.env)
```env
# Application
APP_NAME=Enterprise AI DMS
DEBUG=False
SECRET_KEY=<generate-a-random-secret>
ENVIRONMENT=production

# Database
DATABASE_URL=<enterprise-postgresql-url>

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=<configured-minio-user>
MINIO_SECRET_KEY=<configured-minio-secret>
MINIO_BUCKET=dms-documents

# AI Services
GEMINI_API_KEY=<optional>
HUGGINGFACE_API_KEY=<optional>
OPENROUTER_API_KEY=<optional>
GROQ_API_KEY=<optional>

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<optional>
SMTP_PASSWORD=<optional>
SMTP_FROM=noreply@yourdomain.com

# Security
JWT_SECRET_KEY=<generate-a-random-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

#### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Enterprise AI DMS
```

#### Mobile (Update in src/context/ApiContext.js)
```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# View logs
docker-compose -f infrastructure/docker/docker-compose.yml logs -f

# Stop services
docker-compose -f infrastructure/docker/docker-compose.yml down

# Stop and remove volumes
docker-compose -f infrastructure/docker/docker-compose.yml down -v
```

### Deferred Enterprise Deployment

The production/multi-user deployment stack is intentionally deferred while Personal Local is the active edition. Its Docker, Railway, monitoring, and deployment helpers are preserved under `infrastructure/` and `archive/legacy-enterprise/`.

### Manual Deployment

1. **Database Setup**
```bash
# Create PostgreSQL database
createdb dms

# Run migrations
alembic upgrade head
```

2. **Backend Deployment**
```bash
# Install production dependencies
pip install -r requirements-production.txt

# Start with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **Frontend Deployment**
```bash
# Build for production
npm run build

# Serve with Nginx
# Configure Nginx to serve the build directory
```

4. **Celery Workers**
```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A app.core.celery_app beat --loglevel=info
```

## 📚 API Documentation

### API Endpoints

#### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh token

#### Documents
- `GET /api/documents` - List documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents/{id}` - Get document details
- `DELETE /api/documents/{id}` - Delete document
- `PUT /api/documents/{id}` - Update document

#### Analysis
- `POST /api/analysis/detect-function` - Detect document function
- `POST /api/analysis/detect-fracture` - Detect document quality
- `GET /api/analysis/functions` - Get supported functions
- `POST /api/analysis/comprehensive` - Comprehensive analysis

#### Search
- `POST /api/search/advanced` - Advanced search
- `GET /api/search/suggestions` - Search suggestions

#### Versions
- `POST /api/versions/document/{id}` - Create version
- `GET /api/versions/document/{id}` - Get document versions
- `POST /api/versions/document/{id}/rollback/{version_id}` - Rollback to version
- `GET /api/versions/document/{id}/compare/{v1}/{v2}` - Compare versions

#### Reports
- `POST /api/reports/templates` - Create report template
- `GET /api/reports/templates` - List report templates
- `POST /api/reports/generate/{template_id}` - Generate report
- `POST /api/reports/export` - Export report

#### Integrations
- `POST /api/integrations` - Create integration
- `GET /api/integrations` - List integrations
- `POST /api/integrations/{id}/activate` - Activate integration
- `POST /api/integrations/{id}/sync/erp` - Sync to ERP
- `POST /api/integrations/{id}/sync/crm` - Sync to CRM

#### Monitoring
- `GET /metrics` - Prometheus metrics

### Full API Documentation
Run the application and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📱 Mobile Application

### Features
- JWT authentication
- Document management
- Document upload
- Search functionality
- User profile
- Offline support

### Installation & Running
```bash
cd mobile
npm install
npm start
```

### Building for Production
```bash
# iOS
eas build --platform ios

# Android
eas build --platform android
```

## 📊 Monitoring

### Prometheus & Grafana

Start monitoring stack:
```bash
cd infrastructure/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

Access dashboards:
- Grafana: use the credentials configured for your monitoring deployment
- Prometheus: http://localhost:9090

### Available Dashboards
- **Overview**: System overview and statistics
- **Document Processing**: Document processing metrics
- **System Monitoring**: CPU, memory, disk usage

## 🧪 Testing

### Run All Tests
```bash
cd web-platform/backend
pytest
```

### Run Specific Tests
```bash
# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e

# With coverage
pytest --cov=app --cov-report=html
```

### Test Coverage
View coverage report:
```bash
open htmlcov/index.html
```

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
```

#### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Check Redis URL in .env
```

#### MinIO Connection Issues
```bash
# Check MinIO is running
docker ps | grep minio

# Check MinIO credentials in .env
```

#### OCR Not Working
```bash
# Install Tesseract
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-mya

# macOS
brew install tesseract tesseract-lang

# Download Myanmar language data
wget https://github.com/tesseract-ocr/tessdata/raw/main/mya.traineddata
sudo mv mya.traineddata /usr/share/tesseract-ocr/4.00/tessdata/
```

## 🔒 Security

### Security Features
- JWT authentication
- Role-based access control (RBAC)
- Password hashing (bcrypt)
- API rate limiting
- Audit logging
- Document encryption
- Secure token storage
- CORS protection
- SQL injection prevention
- XSS protection

### Security Best Practices
- Use strong SECRET_KEY
- Enable HTTPS in production
- Regular security updates
- Use environment variables for secrets
- Implement rate limiting
- Monitor logs for suspicious activity
- Regular security audits

## 🤝 Contributing

### Contribution Guidelines
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python
- Follow ESLint rules for JavaScript/TypeScript
- Write descriptive commit messages
- Add documentation for new features

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support and questions:
- Email: support@yourdomain.com
- Documentation: [Documentation Link]
- Issues: [GitHub Issues]

## 🎉 Acknowledgments

- FastAPI team for the excellent framework
- React and React Native communities
- AI service providers (Gemini, Hugging Face, etc.)
- Open source contributors

---

**Built with ❤️ for Enterprise Document Management**