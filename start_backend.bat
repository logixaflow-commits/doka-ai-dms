@echo off
REM Enterprise DMS - Backend Startup Script
REM Starts only the FastAPI backend

echo ========================================
echo Enterprise DMS - Backend Startup
echo ========================================
echo.

cd /d "%~dp0dms"

echo Starting FastAPI Backend on port 8000...
echo Backend API: http://localhost:8000
echo API Docs:   http://localhost:8000/docs
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause