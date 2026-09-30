#!/bin/bash

# Enterprise AI DMS - Automated Deployment Script
# This script automates the deployment process for production

set -e

echo "🚀 Starting Enterprise AI DMS Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="$PROJECT_DIR/deployment.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✓ $1${NC}"
}

# Warning message
warning() {
    log "${YELLOW}⚠ $1${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        error_exit "Please run as root or with sudo"
    fi
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker first."
    fi
    success "Docker is installed"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed. Please install Docker Compose first."
    fi
    success "Docker Compose is installed"
}

# Backup existing data
backup_data() {
    log "Creating backup of existing data..."
    
    # Backup database
    if docker ps | grep -q postgres; then
        docker exec postgres pg_dump dms > "$BACKUP_DIR/database_$(date +%Y%m%d_%H%M%S).sql"
        success "Database backup created"
    fi
    
    # Backup storage
    if [ -d "storage" ]; then
        tar -czf "$BACKUP_DIR/storage_$(date +%Y%m%d_%H%M%S).tar.gz" storage/
        success "Storage backup created"
    fi
}

# Stop existing services
stop_services() {
    log "Stopping existing services..."
    docker-compose -f docker-compose.production.yml down || true
    success "Services stopped"
}

# Pull latest images
pull_images() {
    log "Pulling latest Docker images..."
    docker-compose -f docker-compose.production.yml pull
    success "Docker images pulled"
}

# Build images
build_images() {
    log "Building Docker images..."
    docker-compose -f docker-compose.production.yml build
    success "Docker images built"
}

# Start services
start_services() {
    log "Starting services..."
    docker-compose -f docker-compose.production.yml up -d
    success "Services started"
}

# Wait for services to be healthy
wait_for_services() {
    log "Waiting for services to be healthy..."
    
    # Wait for PostgreSQL
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec postgres pg_isready -U postgres -d dms; then
            success "PostgreSQL is ready"
            break
        fi
        attempt=$((attempt+1))
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        error_exit "PostgreSQL failed to start"
    fi
    
    # Wait for backend
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "Backend is ready"
            break
        fi
        attempt=$((attempt+1))
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        warning "Backend health check failed, but services are running"
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
    success "Database migrations completed"
}

# Initialize database
init_database() {
    log "Initializing database..."
    docker-compose -f docker-compose.production.yml exec backend python -c "from app.core.database import init_database; init_database()"
    success "Database initialized"
}

# Check services status
check_status() {
    log "Checking services status..."
    docker-compose -f docker-compose.production.yml ps
    success "Services status checked"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups (keeping last 7 days)..."
    find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
    success "Old backups cleaned up"
}

# Main deployment function
deploy() {
    log "Starting deployment process..."
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Backup existing data
    backup_data
    
    # Stop existing services
    stop_services
    
    # Pull latest images
    pull_images
    
    # Build images
    build_images
    
    # Start services
    start_services
    
    # Wait for services
    wait_for_services
    
    # Run migrations
    run_migrations
    
    # Initialize database
    init_database
    
    # Check status
    check_status
    
    # Cleanup
    cleanup_backups
    
    success "Deployment completed successfully!"
    log "🎉 Enterprise AI DMS is now running!"
    log "Access the application at: http://localhost:3000"
    log "API documentation at: http://localhost:8000/docs"
}

# Rollback function
rollback() {
    log "Starting rollback process..."
    
    # Stop services
    stop_services
    
    # Restore from latest backup
    LATEST_DB_BACKUP=$(ls -t "$BACKUP_DIR"/database_*.sql 2>/dev/null | head -1)
    LATEST_STORAGE_BACKUP=$(ls -t "$BACKUP_DIR"/storage_*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DB_BACKUP" ]; then
        log "Restoring database from $LATEST_DB_BACKUP"
        docker exec -i postgres psql -U postgres -d dms < "$LATEST_DB_BACKUP"
        success "Database restored"
    fi
    
    if [ -n "$LATEST_STORAGE_BACKUP" ]; then
        log "Restoring storage from $LATEST_STORAGE_BACKUP"
        tar -xzf "$LATEST_STORAGE_BACKUP" -C "$PROJECT_DIR"
        success "Storage restored"
    fi
    
    # Start services
    start_services
    
    success "Rollback completed successfully!"
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    backup)
        backup_data
        cleanup_backups
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|backup|status}"
        exit 1
        ;;
esac