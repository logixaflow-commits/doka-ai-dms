@echo off
setlocal
cd /d "%~dp0"
if not exist "web-platform\backend\.venv\Scripts\python.exe" (
  echo Python environment not found. Run start_application.bat first.
  exit /b 1
)
if not exist "web-platform\backend\.env" (
  copy /Y "web-platform\backend\.env.example" "web-platform\backend\.env" >nul
  echo Created web-platform\backend\.env. Set BOOTSTRAP_ADMIN_PASSWORD before login.
)
"web-platform\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
endlocal
