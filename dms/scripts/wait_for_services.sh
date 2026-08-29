#!/bin/bash
# =============================================================================
# Office DMS - Service Health Check Script
# Waits for all dependent services to be ready before starting the app.
# =============================================================================

set -e

echo "[WAIT] Waiting for services to be ready..."

# Wait for PostgreSQL
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "[WAIT] Checking PostgreSQL..."
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_HOST=${DB_HOST:-db}
    DB_PORT=${DB_PORT:-5432}
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "${DB_USER:-dms_user}" 2>/dev/null; do
        echo "[WAIT] PostgreSQL not ready, waiting..."
        sleep 2
    done
    echo "[WAIT] PostgreSQL is ready!"
fi

# Wait for Redis
echo "[WAIT] Checking Redis..."
REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; do
    echo "[WAIT] Redis not ready, waiting..."
    sleep 2
done
echo "[WAIT] Redis is ready!"

# Wait for MinIO
echo "[WAIT] Checking MinIO..."
MINIO_HOST=$(echo $MINIO_ENDPOINT | cut -d: -f1)
MINIO_PORT=$(echo $MINIO_ENDPOINT | cut -d: -f2)
MINIO_HOST=${MINIO_HOST:-minio}
MINIO_PORT=${MINIO_PORT:-9000}
until curl -f "http://${MINIO_HOST}:${MINIO_PORT}/minio/health/live" 2>/dev/null; do
    echo "[WAIT] MinIO not ready, waiting..."
    sleep 2
done
echo "[WAIT] MinIO is ready!"

echo "[WAIT] All services are ready!"
