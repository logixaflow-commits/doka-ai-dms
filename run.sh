#!/bin/bash

# Enterprise AI DMS Startup Script
# Checks for Docker first, falls back to local Python installation

set -e

echo "=========================================="
echo "Enterprise AI Document Management System"
echo "=========================================="
echo ""

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✓ Docker detected. Using Docker Compose..."
    echo ""
    
    # Check if Docker is running
    if docker info &> /dev/null; then
        echo "✓ Docker is running"
        echo ""
        
        # Start services with Docker Compose
        echo "Starting services with Docker Compose..."
        docker-compose up -d
        
        echo ""
        echo "✓ Services started successfully!"
        echo ""
        echo "Access the application:"
        echo "  - Web Interface: http://localhost:8000"
        echo "  - API Documentation: http://localhost:8000/api/docs"
        echo "  - MinIO Console: http://localhost:9001"
        echo ""
        echo "Default credentials: admin / admin123"
        echo ""
        echo "To stop services: docker-compose down"
        echo "To view logs: docker-compose logs -f"
        
    else
        echo "✗ Docker is not running. Please start Docker and try again."
        echo "  Or use local Python installation (fallback mode)."
        exit 1
    fi
    
else
    echo "✗ Docker not detected. Falling back to local Python installation..."
    echo ""
    
    # Check if Python is available
    if command -v python3 &> /dev/null; then
        echo "✓ Python 3 detected"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        echo "✓ Python detected"
        PYTHON_CMD="python"
    else
        echo "✗ Python not found. Please install Python 3.8+ to continue."
        exit 1
    fi
    
    echo ""
    
    # Check if Tesseract is installed
    if command -v tesseract &> /dev/null; then
        echo "✓ Tesseract OCR detected"
        echo "  Installed languages:"
        tesseract --list-langs
        echo ""
        
        # Check for Myanmar language
        if tesseract --list-langs | grep -q "mya"; then
            echo "✓ Myanmar (mya) language pack found"
        else
            echo "⚠ Myanmar (mya) language pack not found"
            echo "  Install with: sudo apt-get install tesseract-ocr-mya (Linux)"
            echo "  Or: brew install tesseract tesseract-lang (Mac with mya)"
            echo ""
        fi
    else
        echo "⚠ Tesseract OCR not found"
        echo "  Install with: sudo apt-get install tesseract-ocr (Linux)"
        echo "  Or: brew install tesseract (Mac)"
        echo ""
        echo "OCR functionality will be limited without Tesseract."
    fi
    
    echo ""
    echo "Setting up local environment..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r dms/requirements-dev.txt
    
    # Setup environment
    echo "Setting up environment..."
    if [ ! -f ".env" ]; then
        echo "Creating .env file from template..."
        cp dms/.env.example .env 2>/dev/null || cat > .env << EOL
# Local Development Environment
DATABASE_URL=sqlite:///./Office_DMS/database/dms.db
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
SECRET_KEY=dev-secret-key-change-in-production
ENCRYPTION_KEY=
ENVIRONMENT=development
DEBUG=true
TESSERACT_CMD=tesseract
MYANMAR_LANG=mya
SMTP_ENABLED=false
SMTP_SERVER=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@enterprise-dms.local
SMTP_FROM_NAME=Enterprise DMS
ADMIN_EMAIL=admin@enterprise-dms.local
EOL
    fi
    
    # Create necessary directories
    echo "Creating directories..."
    mkdir -p Office_DMS/Watch_Folder
    mkdir -p Office_DMS/Processing_Workspace
    mkdir -p Office_DMS/Organized
    mkdir -p Office_DMS/Duplicate
    mkdir -p Office_DMS/Suspicious
    mkdir -p logs
    
    # Initialize database
    echo "Initializing database..."
    cd dms
    $PYTHON_CMD -c "from app.core.database import init_database; init_database()"
    cd ..
    
    # Start the application
    echo ""
    echo "✓ Local environment setup complete!"
    echo ""
    echo "Starting the application..."
    echo "  - Web Interface: http://localhost:8000"
    echo "  - API Documentation: http://localhost:8000/api/docs"
    echo ""
    echo "Default credentials: admin / admin123"
    echo ""
    
    cd dms
    uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload --factory
fi