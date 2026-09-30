# Multi-stage Dockerfile for Enterprise AI DMS
# Includes Tesseract OCR with Myanmar (mya) language pack support

# Stage 1: Base image with Tesseract and Myanmar language pack
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Tesseract and Myanmar language pack
RUN apt-get update && apt-get install -y \
    # Tesseract OCR and dependencies
    tesseract-ocr \
    tesseract-ocr-mya \
    tesseract-ocr-eng \
    liblept5 \
    libtesseract5 \
    # Image processing dependencies
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    zlib1g-dev \
    # PDF processing
    libpoppler-dev \
    poppler-utils \
    # Build tools
    gcc \
    g++ \
    make \
    # Other utilities
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Verify Myanmar language pack installation
RUN tesseract --list-langs | grep mya || echo "Myanmar language pack verification: FAILED"

# Stage 2: Python dependencies
FROM base as python-deps

WORKDIR /app

# Copy requirements file
COPY dms/requirements-dev.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Stage 3: Application
FROM python-deps as app

WORKDIR /app

# Copy application code
COPY dms/ .

# Create necessary directories
RUN mkdir -p logs Office_DMS/Watch_Folder Office_DMS/Processing_Workspace Office_DMS/Organized Office_DMS/Duplicate Office_DMS/Suspicious

# Set permissions
RUN chmod +x scripts/*.py || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command for web server
CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]

# Stage 4: Celery Worker
FROM python-deps as celery-worker

WORKDIR /app

# Copy application code
COPY dms/ .

# Create necessary directories
RUN mkdir -p logs Office_DMS/Watch_Folder Office_DMS/Processing_Workspace Office_DMS/Organized Office_DMS/Duplicate Office_DMS/Suspicious

# Set permissions
RUN chmod +x scripts/*.py || true

# Default command for Celery worker
CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=4"]

# Stage 5: Celery Beat
FROM python-deps as celery-beat

WORKDIR /app

# Copy application code
COPY dms/ .

# Create necessary directories
RUN mkdir -p logs Office_DMS/Watch_Folder Office_DMS/Processing_Workspace Office_DMS/Organized Office_DMS/Duplicate Office_DMS/Suspicious

# Set permissions
RUN chmod +x scripts/*.py || true

# Default command for Celery beat scheduler
CMD ["celery", "-A", "app.core.celery_app", "beat", "--loglevel=info"]
