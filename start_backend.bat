@echo off
setlocal
cd /d "%~dp0"
if not exist "apps/web-platform\backend\.venv\Scripts\python.exe" (
  echo Python environment not found. Run start_application.bat first.
  exit /b 1
)
if not exist "apps/web-platform\backend\.env" (
  copy /Y "apps/web-platform\backend\.env.example" "apps/web-platform\backend\.env" >nul
  echo Created apps/web-platform\backend\.env. Set BOOTSTRAP_ADMIN_PASSWORD before login.
)
"apps/web-platform\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
endlocal
