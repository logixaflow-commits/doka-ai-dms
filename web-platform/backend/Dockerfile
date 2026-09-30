# =============================================================================
# Office DMS - Multi-Stage Production Dockerfile
# Includes: Tesseract OCR with Myanmar language support
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Production ---
FROM python:3.11-slim

LABEL maintainer="Office DMS Team"
LABEL description="AI Document Management System with OCR and Classification"

WORKDIR /app

# Install runtime dependencies
# Tesseract OCR + Myanmar language data + image libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-mya \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpq5 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Verify Tesseract installation
RUN tesseract --version && tesseract --list-langs

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r dms && useradd -r -g dms -d /app -s /bin/bash dms

# Create required directories
RUN mkdir -p Office_DMS/{Original_Files,Watch_Folder,Processing_Workspace,Organized/{Import/{Supplier_A,Supplier_B,Supplier_C},Export,NRC,Household,FDA,Invoices,BL,Licenses,Government,Association,Other,Review},Duplicate,Suspicious,database,backups} \
    logs \
    app/static/react \
    && chown -R dms:dms /app

# Copy application code
COPY --chown=dms:dms app/ ./app/
COPY --chown=dms:dms config.yaml .
COPY --chown=dms:dms .env.example .env
COPY --chown=dms:dms run.py .

# Switch to non-root user
USER dms

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (overridden by docker-compose for different services)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
