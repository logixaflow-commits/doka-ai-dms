@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Doka AI DMS - Personal Local

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\apps/web-platform\backend"
set "FRONTEND=%ROOT%\apps/web-platform\frontend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"

echo ===================================================
echo           DOKA AI DMS - PERSONAL LOCAL
echo ===================================================
echo [1/4] Checking environment...

if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found at:
    echo         %PYTHON%
    echo Please install dependencies first.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is required but was not found in PATH.
    pause
    exit /b 1
)

echo [2/4] Initializing configuration...
set "PYTHONPATH=%BACKEND%"
set "ORIGINAL_READ_ONLY=true"
set "ALLOW_SOURCE_WRITE=false"

if not defined SOURCE_ROOT (
    if exist "D:\Doka\NEW Sample Ofiice\2 SYM SHEM CO.,LTD" (
        set "SOURCE_ROOT=D:\Doka\NEW Sample Ofiice\2 SYM SHEM CO.,LTD"
    ) else (
        set "SOURCE_ROOT=D:\Doka\DokaPilotCopy"
    )
)
if not defined WORKING_ROOT (
    set "WORKING_ROOT=D:\Doka\Workspace"
)
if not defined FINAL_ROOT (
    set "FINAL_ROOT=%WORKING_ROOT%\Final"
)
if not defined BACKUP_ROOT (
    set "BACKUP_ROOT=D:\Doka\Backups"
)

if not exist "%WORKING_ROOT%" mkdir "%WORKING_ROOT%" 2>nul
if not exist "%FINAL_ROOT%" mkdir "%FINAL_ROOT%" 2>nul
if not exist "%BACKUP_ROOT%" mkdir "%BACKUP_ROOT%" 2>nul

echo       Source   : %SOURCE_ROOT%
echo       Workspace: %WORKING_ROOT%
echo       Final    : %FINAL_ROOT%
echo       Backups  : %BACKUP_ROOT%

echo [3/4] Starting backend and frontend services...
start "Doka Backend" /min cmd /c ""%PYTHON%" -m uvicorn app.main:app --app-dir "%BACKEND%" --host 127.0.0.1 --port 8002"
start "Doka Frontend" /min cmd /c "cd /d "%FRONTEND%" && npm run dev -- --host 127.0.0.1 --port 5173"

echo [4/4] Waiting for services to initialize...
powershell -Command "Start-Sleep -Seconds 4"

echo.
echo ===================================================
echo  Doka AI DMS is running!
echo  URL: http://127.0.0.1:5173
echo.
echo  - To stop Doka, double-click: stop-doka.bat
echo  - To backup workspace, run  : backup-doka.bat
echo ===================================================
echo.

start "" "http://127.0.0.1:5173"
exit /b 0
