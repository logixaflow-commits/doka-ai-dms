#!/bin/bash
# Production Backup Script for Enterprise DMS
# This script performs automated backups of database, files, and configurations

set -e

# Configuration
BACKUP_DIR="/var/backups/enterprise-dms"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/files"
mkdir -p "$BACKUP_DIR/config"

echo "Starting backup at $(date)"

# Backup PostgreSQL Database
echo "Backing up PostgreSQL database..."
docker-compose -f docker-compose.production.yml exec -T postgres pg_dump -U dms_user dms_db > "$BACKUP_DIR/database/dms_db_$TIMESTAMP.sql"
gzip "$BACKUP_DIR/database/dms_db_$TIMESTAMP.sql"
echo "Database backup completed"

# Backup MinIO Data
echo "Backing up MinIO data..."
docker cp dms-minio:/data "$BACKUP_DIR/files/minio_data_$TIMESTAMP"
tar -czf "$BACKUP_DIR/files/minio_data_$TIMESTAMP.tar.gz" "$BACKUP_DIR/files/minio_data_$TIMESTAMP"
rm -rf "$BACKUP_DIR/files/minio_data_$TIMESTAMP"
echo "MinIO backup completed"

# Backup Uploads
echo "Backing up uploaded files..."
docker cp dms-backend:/app/uploads "$BACKUP_DIR/files/uploads_$TIMESTAMP"
tar -czf "$BACKUP_DIR/files/uploads_$TIMESTAMP.tar.gz" "$BACKUP_DIR/files/uploads_$TIMESTAMP"
rm -rf "$BACKUP_DIR/files/uploads_$TIMESTAMP"
echo "Uploads backup completed"

# Backup Configuration Files
echo "Backing up configuration files..."
cp dms/.env.production "$BACKUP_DIR/config/.env.production_$TIMESTAMP"
cp nginx/nginx.conf "$BACKUP_DIR/config/nginx.conf_$TIMESTAMP"
echo "Configuration backup completed"

# Clean old backups
echo "Cleaning old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete
echo "Old backups cleaned"

# Create backup manifest
echo "Backup completed at $(date)" > "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"
echo "Database: dms_db_$TIMESTAMP.sql.gz" >> "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"
echo "MinIO: minio_data_$TIMESTAMP.tar.gz" >> "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"
echo "Uploads: uploads_$TIMESTAMP.tar.gz" >> "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"
echo "Config: .env.production_$TIMESTAMP, nginx.conf_$TIMESTAMP" >> "$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"

echo "Backup completed successfully at $(date)"
echo "Backup location: $BACKUP_DIR"