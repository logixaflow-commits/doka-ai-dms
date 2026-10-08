@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Final acceptance runner for Gates 3-6.
REM Required environment variables:
REM   DOKA_PILOT_SOURCE      copied representative office dataset
REM   DOKA_PILOT_WORKSPACE   EMPTY dedicated workspace
REM   DOKA_PILOT_BACKUPS     dedicated backup directory
REM   DOKA_OCR_ROOT          copied OCR benchmark samples
REM   DOKA_OCR_MANIFEST      OCR manifest JSON
REM   BOOTSTRAP_ADMIN_PASSWORD  local acceptance password (never committed)

if "%DOKA_PILOT_SOURCE%"=="" echo Set DOKA_PILOT_SOURCE first.& exit /b 2
if "%DOKA_PILOT_WORKSPACE%"=="" echo Set DOKA_PILOT_WORKSPACE first.& exit /b 2
if "%DOKA_PILOT_BACKUPS%"=="" echo Set DOKA_PILOT_BACKUPS first.& exit /b 2
if "%DOKA_OCR_ROOT%"=="" echo Set DOKA_OCR_ROOT first.& exit /b 2
if "%DOKA_OCR_MANIFEST%"=="" echo Set DOKA_OCR_MANIFEST first.& exit /b 2
if "%BOOTSTRAP_ADMIN_PASSWORD%"=="" echo Set BOOTSTRAP_ADMIN_PASSWORD first.& exit /b 2

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\web-platform\backend"
set "FRONTEND=%ROOT%\web-platform\frontend"
set "VENV=%ROOT%\.acceptance-venv"
set "EVIDENCE=%ROOT%\Phase0_Evidence\acceptance"
if not exist "%EVIDENCE%" mkdir "%EVIDENCE%"

python -m venv "%VENV%"
if errorlevel 1 exit /b 1
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%VENV%\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements-local.txt" -r "%BACKEND%\requirements-test.txt"
if errorlevel 1 exit /b 1

set ENVIRONMENT=development
set DEBUG=false
set SOURCE_ROOT=%DOKA_PILOT_SOURCE%
set WORKING_ROOT=%DOKA_PILOT_WORKSPACE%
set FINAL_ROOT=%DOKA_PILOT_WORKSPACE%\Final
set QUARANTINE_ROOT=%DOKA_PILOT_WORKSPACE%\Quarantine
set BACKUP_ROOT=%DOKA_PILOT_BACKUPS%
set ORIGINAL_READ_ONLY=true
set ALLOW_SOURCE_WRITE=false
set LOCAL_ADMIN_USERNAME=admin
set CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000

"%VENV%\Scripts\python.exe" "%ROOT%\scripts\ocr_benchmark.py" --root "%DOKA_OCR_ROOT%" --manifest "%DOKA_OCR_MANIFEST%" --output "%EVIDENCE%\gate-3-ocr.json"
if errorlevel 1 exit /b 3

"%VENV%\Scripts\python.exe" "%ROOT%\scripts\doka_pilot_check.py" --source "%DOKA_PILOT_SOURCE%" --workspace "%DOKA_PILOT_WORKSPACE%" --backup-root "%DOKA_PILOT_BACKUPS%" --output "%EVIDENCE%\gate-5-pilot-gate-6-recovery.json" --require-ocr
if errorlevel 1 exit /b 5

cd /d "%FRONTEND%"
npm ci
if errorlevel 1 exit /b 1
npx playwright install chromium
if errorlevel 1 exit /b 1
npm run build
if errorlevel 1 exit /b 1

set DOKA_E2E_SOURCE_DIR=%DOKA_PILOT_SOURCE%
set DOKA_E2E_USERNAME=admin
set DOKA_E2E_PASSWORD=%BOOTSTRAP_ADMIN_PASSWORD%

start "Doka Backend" /b cmd /c "\"%VENV%\Scripts\python.exe\" -m uvicorn app.main:app --app-dir \"%BACKEND%\" --host 127.0.0.1 --port 8000 > \"%EVIDENCE%\backend.log\" 2>&1"
start "Doka Frontend" /b cmd /c "npm run dev -- --host 127.0.0.1 --port 3000 > \"%EVIDENCE%\frontend.log\" 2>&1"
timeout /t 5 /nobreak >nul
npm run test:e2e:local
exit /b %errorlevel%
