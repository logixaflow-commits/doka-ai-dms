#!/bin/bash

# Enterprise AI DMS - Health Check Script
# Check system health and service status

echo "🏥 Checking Enterprise AI DMS Health..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HEALTHY=0
UNHEALTHY=0

check_service() {
    if docker ps | grep -q "$1"; then
        echo "${GREEN}✓${NC} $1 is running"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} $1 is not running"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_api() {
    if curl -f -s http://localhost:8000/health > /dev/null; then
        echo "${GREEN}✓${NC} Backend API is healthy"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} Backend API is unhealthy"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_frontend() {
    if curl -f -s http://localhost:3000 > /dev/null; then
        echo "${GREEN}✓${NC} Frontend is accessible"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} Frontend is not accessible"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_database() {
    if docker exec postgres pg_isready -U postgres -d dms > /dev/null 2>&1; then
        echo "${GREEN}✓${NC} Database is ready"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} Database is not ready"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_redis() {
    if docker exec redis redis-cli ping > /dev/null 2>&1; then
        echo "${GREEN}✓${NC} Redis is ready"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} Redis is not ready"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_minio() {
    if curl -f -s http://localhost:9000/minio/health/live > /dev/null; then
        echo "${GREEN}✓${NC} MinIO is accessible"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${RED}✗${NC} MinIO is not accessible"
        UNHEALTHY=$((UNHEALTHY+1))
    fi
}

check_disk_space() {
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 80 ]; then
        echo "${GREEN}✓${NC} Disk usage: ${DISK_USAGE}%"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${YELLOW}⚠${NC} Disk usage: ${DISK_USAGE}% (high)"
    fi
}

check_memory() {
    MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$MEM_USAGE" -lt 80 ]; then
        echo "${GREEN}✓${NC} Memory usage: ${MEM_USAGE}%"
        HEALTHY=$((HEALTHY+1))
    else
        echo "${YELLOW}⚠${NC} Memory usage: ${MEM_USAGE}% (high)"
    fi
}

echo "Checking Docker services..."
check_service "postgres"
check_service "redis"
check_service "minio"
check_service "backend"
check_service "frontend"

echo ""
echo "Checking service health..."
check_database
check_redis
check_minio
check_api
check_frontend

echo ""
echo "Checking system resources..."
check_disk_space
check_memory

echo ""
echo "Health Check Summary:"
echo "Healthy: $HEALTHY"
echo "Unhealthy: $UNHEALTHY"

if [ $UNHEALTHY -eq 0 ]; then
    echo "${GREEN}✓ All systems are healthy!${NC}"
    exit 0
else
    echo "${RED}✗ Some systems are unhealthy${NC}"
    exit 1
fi