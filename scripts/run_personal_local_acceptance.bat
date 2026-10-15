@echo off
setlocal EnableExtensions

REM Final acceptance runner for Gates 3-6. Use only dedicated COPY/test paths.
REM Required: DOKA_PILOT_SOURCE, DOKA_PILOT_WORKSPACE, DOKA_PILOT_BACKUPS,
REM DOKA_OCR_ROOT, DOKA_OCR_MANIFEST, BOOTSTRAP_ADMIN_PASSWORD.

if not defined DOKA_PILOT_SOURCE (
  echo Set DOKA_PILOT_SOURCE to a COPY of representative office data.
  exit /b 2
)
if not defined DOKA_PILOT_WORKSPACE (
  echo Set DOKA_PILOT_WORKSPACE to a dedicated EMPTY workspace.
  exit /b 2
)
if not defined DOKA_PILOT_BACKUPS (
  echo Set DOKA_PILOT_BACKUPS to a dedicated backup directory.
  exit /b 2
)
if not defined DOKA_OCR_ROOT (
  echo Set DOKA_OCR_ROOT to copied OCR samples.
  exit /b 2
)
if not defined DOKA_OCR_MANIFEST (
  echo Set DOKA_OCR_MANIFEST to the verified manifest JSON.
  exit /b 2
)
if not defined BOOTSTRAP_ADMIN_PASSWORD (
  echo Set BOOTSTRAP_ADMIN_PASSWORD for this local acceptance run.
  exit /b 2
)

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "BACKEND=%ROOT%\apps/web-platform\backend"
set "FRONTEND=%ROOT%\apps/web-platform\frontend"
set "VENV=%ROOT%\.acceptance-venv"
set "EVIDENCE=%ROOT%\Phase0_Evidence\acceptance"

REM Force the first acceptance pass to remain local-only and read-only.
set "AI_ENABLED=false"
set "AI_EXTERNAL_PROCESSING_CONSENT=false"
set "DOKA_STORAGE_PROVIDER=disabled"
set "ORIGINAL_READ_ONLY=true"
set "ALLOW_SOURCE_WRITE=false"
python "%ROOT%\scripts\local_acceptance_preflight.py" --evidence-root "%EVIDENCE%" --output "%EVIDENCE%\preflight.json"
if errorlevel 1 exit /b 2

if not exist "%EVIDENCE%" mkdir "%EVIDENCE%"
python -m venv "%VENV%"
if errorlevel 1 exit /b 1
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%VENV%\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements-local.txt" -r "%BACKEND%\requirements-test.txt"
if errorlevel 1 exit /b 1

set "ENVIRONMENT=development"
set "DEBUG=false"
set "SOURCE_ROOT=%DOKA_PILOT_SOURCE%"
set "WORKING_ROOT=%DOKA_PILOT_WORKSPACE%"
set "FINAL_ROOT=%DOKA_PILOT_WORKSPACE%\Final"
set "QUARANTINE_ROOT=%DOKA_PILOT_WORKSPACE%\Quarantine"
set "BACKUP_ROOT=%DOKA_PILOT_BACKUPS%"
set "LOCAL_ADMIN_USERNAME=admin"
set "CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000"
for /f %%K in ('"%VENV%\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(32))"') do set "SECRET_KEY=%%K"

"%VENV%\Scripts\python.exe" "%ROOT%\scripts\ocr_benchmark.py" --root "%DOKA_OCR_ROOT%" --manifest "%DOKA_OCR_MANIFEST%" --output "%EVIDENCE%\gate-3-ocr.json"
if errorlevel 1 exit /b 3

"%VENV%\Scripts\python.exe" "%ROOT%\scripts\doka_pilot_check.py" --source "%DOKA_PILOT_SOURCE%" --workspace "%DOKA_PILOT_WORKSPACE%" --backup-root "%DOKA_PILOT_BACKUPS%" --output "%EVIDENCE%\gate-5-pilot-gate-6-recovery.json" --require-ocr
if errorlevel 1 exit /b 5

cd /d "%FRONTEND%"
if errorlevel 1 exit /b 1
npm ci
if errorlevel 1 exit /b 1
npx playwright install chromium
if errorlevel 1 exit /b 1
npm run build
if errorlevel 1 exit /b 1

set "DOKA_E2E_SOURCE_DIR=%DOKA_PILOT_SOURCE%"
set "DOKA_E2E_USERNAME=admin"
set "DOKA_E2E_PASSWORD=%BOOTSTRAP_ADMIN_PASSWORD%"

start "Doka Backend" /b cmd /c ""%VENV%\Scripts\python.exe" -m uvicorn app.main:app --app-dir "%BACKEND%" --host 127.0.0.1 --port 8000 > "%EVIDENCE%\backend.log" 2>&1"
start "Doka Frontend" /b cmd /c "npm run dev -- --host 127.0.0.1 --port 3000 > "%EVIDENCE%\frontend.log" 2>&1"
timeout /t 5 /nobreak >nul
npm run test:e2e:local
set "RESULT=%errorlevel%"
echo Acceptance E2E exit code: %RESULT%
echo If a test failed, inspect the private logs under the acceptance evidence directory.
exit /b %RESULT%
