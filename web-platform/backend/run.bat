@echo off
REM =============================================================================
REM Office DMS - Startup Script (Windows)
REM =============================================================================

echo ============================================================
echo   Office DMS - AI Document Management System
echo   Version 1.0.0
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

REM Check if .env exists
if not exist .env (
    echo [WARN] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo [WARN] Please review and update .env with your settings.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is required but not installed.
    exit /b 1
)

REM Create virtual environment if not exists
if not exist venv (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [SETUP] Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Check Tesseract
echo [CHECK] Verifying Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Tesseract not found. OCR will not work.
    echo [WARN] Download from: https://github.com/UB-Mannheim/tesseract/wiki
) else (
    echo [CHECK] Tesseract is installed.
)

REM Initialize database
echo [INIT] Initializing database...
python run.py --init

REM Start server
echo [SERVER] Starting FastAPI server...
echo [SERVER] Access: http://localhost:8000
echo [SERVER] Default login: admin / admin123
echo ============================================================

python run.py --host 0.0.0.0 --port 8000 %*
