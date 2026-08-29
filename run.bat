@echo off
REM Enterprise AI DMS Startup Script for Windows
REM Checks for Docker first, falls back to local Python installation

echo ==========================================
echo Enterprise AI Document Management System
echo ==========================================
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Docker not detected. Falling back to local Python installation...
    echo.
    goto local_python
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Docker Compose not detected. Falling back to local Python installation...
    echo.
    goto local_python
)

echo ✓ Docker detected. Using Docker Compose...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Docker is not running. Please start Docker Desktop and try again.
    echo   Or use local Python installation (fallback mode).
    pause
    exit /b 1
)

echo ✓ Docker is running
echo.

REM Start services with Docker Compose
echo Starting services with Docker Compose...
docker-compose up -d

echo.
echo ✓ Services started successfully!
echo.
echo Access the application:
echo   - Web Interface: http://localhost:8000
echo   - API Documentation: http://localhost:8000/api/docs
echo   - MinIO Console: http://localhost:9001
echo.
echo Default credentials: admin / admin123
echo.
echo To stop services: docker-compose down
echo To view logs: docker-compose logs -f
echo.
pause
exit /b 0

:local_python
REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ✗ Python not found. Please install Python 3.8+ to continue.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
        echo ✓ Python 3 detected
    )
) else (
    set PYTHON_CMD=python
    echo ✓ Python detected
)

echo.

REM Check if Tesseract is installed
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠ Tesseract OCR not found
    echo   Install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo   Include Myanmar (mya) language data during installation
    echo.
    echo OCR functionality will be limited without Tesseract.
) else (
    echo ✓ Tesseract OCR detected
    echo   Installed languages:
    tesseract --list-langs
    echo.
    
    REM Check for Myanmar language
    tesseract --list-langs | findstr /C:"mya" >nul 2>&1
    if %errorlevel% neq 0 (
        echo ⚠ Myanmar (mya) language pack not found
        echo   Download from: https://github.com/tesseract-ocr/tessdata
        echo   Place mya.traineddata in tessdata directory
        echo.
    ) else (
        echo ✓ Myanmar (mya) language pack found
    )
)

echo.
echo Setting up local environment...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r dms\requirements-dev.txt

REM Setup environment
echo Setting up environment...
if not exist ".env" (
    echo Creating .env file from template...
    (
        echo # Local Development Environment
        echo DATABASE_URL=sqlite:///./Office_DMS/database/dms.db
        echo REDIS_URL=redis://localhost:6379/0
        echo MINIO_ENDPOINT=localhost:9000
        echo MINIO_ACCESS_KEY=minioadmin
        echo MINIO_SECRET_KEY=minioadmin
        echo MINIO_SECURE=false
        echo SECRET_KEY=dev-secret-key-change-in-production
        echo ENCRYPTION_KEY=
        echo ENVIRONMENT=development
        echo DEBUG=true
        echo TESSERACT_CMD=tesseract
        echo MYANMAR_LANG=mya
        echo SMTP_ENABLED=false
        echo SMTP_SERVER=localhost
        echo SMTP_PORT=587
        echo SMTP_USERNAME=
        echo SMTP_PASSWORD=
        echo SMTP_USE_TLS=true
        echo SMTP_FROM_EMAIL=noreply@enterprise-dms.local
        echo SMTP_FROM_NAME=Enterprise DMS
        echo ADMIN_EMAIL=admin@enterprise-dms.local
    ) > .env
)

REM Create necessary directories
echo Creating directories...
if not exist "Office_DMS\Watch_Folder" mkdir Office_DMS\Watch_Folder
if not exist "Office_DMS\Processing_Workspace" mkdir Office_DMS\Processing_Workspace
if not exist "Office_DMS\Organized" mkdir Office_DMS\Organized
if not exist "Office_DMS\Duplicate" mkdir Office_DMS\Duplicate
if not exist "Office_DMS\Suspicious" mkdir Office_DMS\Suspicious
if not exist "logs" mkdir logs

REM Initialize database
echo Initializing database...
cd dms
%PYTHON_CMD% -c "from app.core.database import init_database; init_database()"
cd ..

echo.
echo ✓ Local environment setup complete!
echo.
echo Starting the application...
echo   - Web Interface: http://localhost:8000
echo   - API Documentation: http://localhost:8000/api/docs
echo.
echo Default credentials: admin / admin123
echo.

cd dms
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload --factory
