# 🚀 Enterprise DMS - Production Setup Guide

## 📋 Overview

This guide provides step-by-step instructions for deploying the Enterprise AI Document Management System to production.

## 🔧 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows Server
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 100GB SSD
- **CPU**: 4+ cores recommended

### Software Requirements
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: Latest version
- **SSL Certificate**: For HTTPS (Let's Encrypt recommended)

## 🚀 Production Deployment Steps

### Step 1: Server Preparation

#### Linux (Ubuntu/Debian)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt install nginx -y

# Install SSL Certificates (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx -y
```

#### Windows Server
```powershell
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop
# Install Git
# Download from: https://git-scm.com/download/win
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/T2W1-LOGIXA-FLOW/enterprise-ai-dms.git
cd enterprise-ai-dms
```

### Step 3: Environment Configuration

```bash
# Copy environment template
cd dms
cp .env.example .env.production

# Edit production environment
nano .env.production
```

**Critical Settings to Configure:**
```env
# Security
SECRET_KEY=generate_with_openssl -base64 32
ENCRYPTION_KEY=generate_with_python_fernet

# Database
POSTGRES_PASSWORD=strong_password_here
DATABASE_URL=postgresql://dms_user:strong_password@postgres:5432/dms_db

# Redis
REDIS_PASSWORD=strong_redis_password
REDIS_URL=redis://:strong_redis_password@redis:6379/0

# MinIO
MINIO_ACCESS_KEY=strong_minio_access_key
MINIO_SECRET_KEY=strong_minio_secret_key

# SMTP (for email notifications)
SMTP_ENABLED=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Step 4: SSL Certificate Setup

#### Using Let's Encrypt (Linux)
```bash
# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

#### Self-Signed Certificate (Development/Testing)
```bash
# Generate self-signed certificate
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

### Step 5: Update Nginx Configuration

Edit `nginx/nginx.conf`:
```nginx
server_name yourdomain.com;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### Step 6: Build and Start Services

```bash
# Build production Docker images
docker-compose -f docker-compose.production.yml build

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check service status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### Step 7: Database Initialization

```bash
# Run database migrations
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.core.database import init_database
init_database()
"

# Create admin user
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.main import seed_admin_user
seed_admin_user()
"
```

### Step 8: Health Check

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API documentation
curl http://localhost:8000/docs
```

## 🔒 Security Hardening

### 1. Firewall Configuration
```bash
# Ubuntu UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 2. Docker Security
```bash
# Enable Docker content trust
export DOCKER_CONTENT_TRUST=1

# Use non-root user in containers
# (Already configured in Dockerfile)
```

### 3. Application Security
- ✅ Environment variables secured
- ✅ SSL/TLS enabled
- ✅ CORS restricted
- ✅ Rate limiting enabled
- ✅ Input validation
- ✅ SQL injection prevention
- ✅ XSS protection

## 📊 Monitoring

### 1. Application Monitoring
```bash
# View application logs
docker-compose -f docker-compose.production.yml logs -f backend

# View all logs
docker-compose -f docker-compose.production.yml logs
```

### 2. System Monitoring
```bash
# Container resource usage
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

### 3. Database Monitoring
```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.production.yml exec postgres psql -U dms_user -d dms_db

# Check database size
SELECT pg_size_pretty(pg_database_size('dms_db'));
```

## 🔄 Backup Strategy

### 1. Database Backup
```bash
# Backup PostgreSQL
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U dms_user dms_db > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
docker-compose -f docker-compose.production.yml exec -T postgres psql -U dms_user dms_db < backup_20240101.sql
```

### 2. File Backup
```bash
# Backup MinIO data
docker cp dms-minio:/data ./backup/minio_data_$(date +%Y%m%d)

# Backup uploads
docker cp dms-backend:/app/uploads ./backup/uploads_$(date +%Y%m%d)
```

### 3. Automated Backup
```bash
# Add to crontab
0 2 * * * cd /path/to/enterprise-ai-dms && ./scripts/backup.sh
```

## 🚀 Performance Optimization

### 1. Database Optimization
```sql
-- Create indexes
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_users_username ON users(username);

-- Analyze tables
ANALYZE documents;
ANALYZE users;
```

### 2. Application Optimization
- ✅ Database connection pooling configured
- ✅ Redis caching enabled
- ✅ Gzip compression enabled
- ✅ Static file caching configured
- ✅ Celery workers for background tasks

### 3. Server Optimization
```bash
# Increase file descriptors
ulimit -n 65536

# Optimize TCP settings
sysctl -w net.core.somaxconn=65536
sysctl -w net.ipv4.tcp_max_syn_backlog=65536
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Container won't start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs backend

# Check resource usage
docker stats

# Restart services
docker-compose -f docker-compose.production.yml restart
```

#### 2. Database connection failed
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.production.yml ps postgres

# Check database logs
docker-compose -f docker-compose.production.yml logs postgres

# Verify connection string
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.core.database import engine
print(engine.url)
"
```

#### 3. Redis connection failed
```bash
# Check Redis status
docker-compose -f docker-compose.production.yml ps redis

# Test Redis connection
docker-compose -f docker-compose.production.yml exec redis redis-cli ping
```

#### 4. High memory usage
```bash
# Check container memory
docker stats --no-stream

# Reduce worker count
# Edit docker-compose.production.yml
# celery-worker:
#   command: celery -A app.core.celery_app worker --loglevel=info --concurrency=2
```

## 📝 Maintenance

### Daily Tasks
- Monitor application logs
- Check disk space
- Review backup status

### Weekly Tasks
- Review security logs
- Update dependencies
- Performance review

### Monthly Tasks
- Security audit
- Dependency updates
- Backup verification
- SSL certificate renewal

## 🎯 Scaling

### Horizontal Scaling
```bash
# Scale backend
docker-compose -f docker-compose.production.yml up -d --scale backend=3

# Scale Celery workers
docker-compose -f docker-compose.production.yml up -d --scale celery-worker=5
```

### Load Balancing
```nginx
# Add multiple backend servers
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review documentation
- Check GitHub issues
- Contact support team

---

## ✅ Production Checklist

- [ ] Server prepared and updated
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] Environment variables configured
- [ ] SSL certificate obtained
- [ ] Nginx configured
- [ ] Docker images built
- [ ] Services started successfully
- [ ] Database initialized
- [ ] Admin user created
- [ ] Health checks passing
- [ ] Backup strategy configured
- [ ] Monitoring configured
- [ ] Security hardening completed
- [ ] Performance optimized
- [ ] Documentation updated

---

**Status**: Production Ready  
**Security**: Enterprise Grade  
**Performance**: Optimized  
**Scalability**: Horizontal & Vertical Scaling Supported