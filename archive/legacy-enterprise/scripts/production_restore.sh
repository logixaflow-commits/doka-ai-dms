#!/bin/bash
# Production Restore Script for Enterprise DMS
# This script restores backups of database, files, and configurations

set -e

# Configuration
BACKUP_DIR="/var/backups/enterprise-dms"
TIMESTAMP=$1

if [ -z "$TIMESTAMP" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20240101_120000"
    exit 1
fi

echo "Starting restore from backup: $TIMESTAMP"

# Stop services
echo "Stopping services..."
docker-compose -f docker-compose.production.yml stop

# Restore PostgreSQL Database
echo "Restoring PostgreSQL database..."
if [ -f "$BACKUP_DIR/database/dms_db_$TIMESTAMP.sql.gz" ]; then
    gunzip -c "$BACKUP_DIR/database/dms_db_$TIMESTAMP.sql.gz" | docker-compose -f docker-compose.production.yml exec -T postgres psql -U dms_user dms_db
    echo "Database restore completed"
else
    echo "Database backup not found"
fi

# Restore MinIO Data
echo "Restoring MinIO data..."
if [ -f "$BACKUP_DIR/files/minio_data_$TIMESTAMP.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/files/minio_data_$TIMESTAMP.tar.gz" -C /tmp
    docker cp /tmp/minio_data_$TIMESTAMP/* dms-minio:/data/
    rm -rf /tmp/minio_data_$TIMESTAMP
    echo "MinIO restore completed"
else
    echo "MinIO backup not found"
fi

# Restore Uploads
echo "Restoring uploaded files..."
if [ -f "$BACKUP_DIR/files/uploads_$TIMESTAMP.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/files/uploads_$TIMESTAMP.tar.gz" -C /tmp
    docker cp /tmp/uploads_$TIMESTAMP/* dms-backend:/app/uploads/
    rm -rf /tmp/uploads_$TIMESTAMP
    echo "Uploads restore completed"
else
    echo "Uploads backup not found"
fi

# Restore Configuration Files
echo "Restoring configuration files..."
if [ -f "$BACKUP_DIR/config/.env.production_$TIMESTAMP" ]; then
    cp "$BACKUP_DIR/config/.env.production_$TIMESTAMP" dms/.env.production
    echo "Environment configuration restored"
fi

if [ -f "$BACKUP_DIR/config/nginx.conf_$TIMESTAMP" ]; then
    cp "$BACKUP_DIR/config/nginx.conf_$TIMESTAMP" nginx/nginx.conf
    echo "Nginx configuration restored"
fi

# Restart services
echo "Restarting services..."
docker-compose -f docker-compose.production.yml up -d

echo "Restore completed successfully at $(date)"