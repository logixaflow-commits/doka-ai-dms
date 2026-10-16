# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+
- Node.js 18+
- PostgreSQL 14+ (if not using Docker)
- Redis 7+ (if not using Docker)
- Domain name (for production)
- SSL certificate (for production)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd Enterprise-AI-DMS-Blueprint
```

### 2. Configure Environment Variables

#### Backend (.env)
```bash
cd dms
cp .env.example .env
# Edit .env with your configuration
```

#### Frontend (.env.local)
```bash
cd app
cp .env.example .env.local
# Edit .env.local with your configuration
```

### 3. Generate Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Docker Deployment

### Development Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Start production services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Stop services
docker-compose -f docker-compose.production.yml down
```

## Manual Deployment

### Backend Deployment

#### 1. Install Dependencies

```bash
cd dms
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-production.txt
```

#### 2. Setup Database

```bash
# Create PostgreSQL database
createdb dms

# Run migrations
alembic upgrade head
```

#### 3. Start Application

```bash
# Start with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### 4. Start Celery Workers

```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat
celery -A app.core.celery_app beat --loglevel=info
```

### Frontend Deployment

#### 1. Install Dependencies

```bash
cd app
npm install
```

#### 2. Build for Production

```bash
npm run build
```

#### 3. Serve with Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /path/to/app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Mobile Application Deployment

#### 1. Build for iOS

```bash
cd mobile
eas build --platform ios
```

#### 2. Build for Android

```bash
eas build --platform android
```

#### 3. Submit to App Stores

```bash
# iOS
eas submit --platform ios

# Android
eas submit --platform android
```

## Monitoring Deployment

### Start Monitoring Stack

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### Access Monitoring

- Grafana: http://localhost:3001 (admin/admin123)
- Prometheus: http://localhost:9090

## SSL Configuration

### Using Let's Encrypt

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Manual SSL

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

## Backup Strategy

### Database Backup

```bash
# Backup PostgreSQL
pg_dump dms > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql dms < backup_20250101.sql
```

### File Backup

```bash
# Backup MinIO data
docker exec minio mc mirror /data /backup/minio

# Backup storage directory
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup"

# Database backup
pg_dump dms > $BACKUP_DIR/database_$DATE.sql

# File backup
tar -czf $BACKUP_DIR/storage_$DATE.tar.gz storage/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_created_at ON documents(created_at);

-- Analyze tables
ANALYZE documents;
ANALYZE users;
```

### Redis Configuration

```bash
# Edit redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Nginx Optimization

```nginx
# Nginx configuration
worker_processes auto;
worker_connections 1024;

# Enable gzip
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs <service_name>

# Check resource usage
docker stats

# Restart container
docker-compose restart <service_name>
```

### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -U postgres -d dms

# Reset connection
docker-compose restart postgres
```

### Performance Issues

```bash
# Check system resources
htop

# Check database performance
SELECT * FROM pg_stat_activity;

# Check Redis performance
redis-cli info stats
```

## Security Hardening

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Application Security

- Use strong SECRET_KEY
- Enable HTTPS
- Implement rate limiting
- Regular security updates
- Monitor logs
- Use environment variables for secrets

## Maintenance

### Regular Tasks

- Update dependencies monthly
- Security patches weekly
- Database backups daily
- Log rotation weekly
- SSL certificate renewal quarterly

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check database
pg_isready -d dms

# Check Redis
redis-cli ping
```

## Scaling

### Horizontal Scaling

```bash
# Scale backend
docker-compose up -d --scale backend=3

# Scale workers
docker-compose up -d --scale worker=4
```

### Load Balancing

```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

## Rollback Strategy

### Application Rollback

```bash
# Rollback to previous commit
git checkout <previous-commit>
docker-compose down
docker-compose up -d
```

### Database Rollback

```bash
# Restore from backup
psql dms < backup_20250101.sql

# Rollback migration
alembic downgrade -1
```

## Monitoring Alerts

### Set Up Alerts

- CPU usage > 80%
- Memory usage > 90%
- Disk usage > 85%
- Response time > 5s
- Error rate > 5%

### Notification Channels

- Email alerts
- Slack notifications
- PagerDuty integration
- SMS alerts for critical issues