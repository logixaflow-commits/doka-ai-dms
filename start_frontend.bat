@echo off
REM Enterprise DMS - Frontend Startup Script
REM Starts only the React frontend

echo ========================================
echo Enterprise DMS - Frontend Startup
echo ========================================
echo.

cd /d "%~dp0app"

echo Installing dependencies if needed...
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

echo Starting React development server on port 3000...
echo Frontend: http://localhost:3000
echo.

npm run dev

pause