@echo off
setlocal
cd /d "%~dp0"
if not exist "dms\.venv\Scripts\python.exe" (
  echo Python environment not found. Run start_application.bat first.
  exit /b 1
)
if not exist "dms\.env" (
  copy /Y "dms\.env.example" "dms\.env" >nul
  echo Created dms\.env. Set BOOTSTRAP_ADMIN_PASSWORD before login.
)
"dms\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
endlocal
