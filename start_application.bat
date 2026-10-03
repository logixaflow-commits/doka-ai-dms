@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Personal Local DMS - Startup
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python was not found.
  exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js was not found.
  exit /b 1
)

if not exist "web-platform\backend\.venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv web-platform\backend\.venv
  if errorlevel 1 exit /b 1
)

if not exist "web-platform\backend\.env" (
  copy /Y "web-platform\backend\.env.example" "web-platform\backend\.env" >nul
  echo Created web-platform\backend\.env from the template.
  echo IMPORTANT: Set BOOTSTRAP_ADMIN_PASSWORD in web-platform\backend\.env before login.
)

echo Installing local Python dependencies...
"web-platform\backend\.venv\Scripts\python.exe" -m pip install -r web-platform\backend\requirements-local.txt
if errorlevel 1 exit /b 1

if not exist "web-platform\frontend\node_modules" (
  echo Installing frontend dependencies...
  cd web-platform\frontend
  npm ci
  if errorlevel 1 exit /b 1
  cd ..
)

echo.
echo Starting backend on http://127.0.0.1:8000 ...
start "Personal DMS Backend" /D "%~dp0web-platform\backend" "%~dp0web-platform\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

timeout /t 2 /nobreak >nul

echo Starting frontend on http://127.0.0.1:3000 ...
start "Personal DMS Frontend" /D "%~dp0web-platform\frontend" cmd /k "npm run dev"

echo.
echo Backend:  http://127.0.0.1:8000/health
echo Frontend: http://127.0.0.1:3000
echo.
echo Original source protection: ORIGINAL_READ_ONLY=true, ALLOW_SOURCE_WRITE=false
echo AI: OFF by default
echo.
endlocal
