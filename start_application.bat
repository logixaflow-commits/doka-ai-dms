@echo off
REM Enterprise DMS - Application Startup Script
REM Starts both Backend (FastAPI) and Frontend (React)

echo ========================================
echo Enterprise DMS - Application Startup
echo ========================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js first.
    pause
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Please install Node.js first.
    pause
    exit /b 1
)

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo Starting Backend (FastAPI) on port 8000...
echo Starting Frontend (React) on port 3000...
echo.

REM Start Backend in background
cd /d "%~dp0dms"
start "DMS Backend" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend
cd /d "%~dp0app"
echo Installing frontend dependencies if needed...
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

echo Starting React development server...
start "DMS Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo Application Started!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend:   http://localhost:3000
echo API Docs:   http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the servers, or close the windows.
echo.
echo Note: This script opens two command windows.
echo Close both windows to stop the application completely.
echo.

REM Open browser automatically
timeout /t 2 /nobreak >nul
start http://localhost:3000

pause
