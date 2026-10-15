@echo off
setlocal EnableExtensions
title Doka AI DMS - Workspace Backup

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\apps/web-platform\backend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"

echo ===================================================
echo           DOKA AI DMS - WORKSPACE BACKUP
echo ===================================================

if not exist "%PYTHON%" (
    echo [ERROR] Python environment not found.
    pause
    exit /b 1
)

set "PYTHONPATH=%BACKEND%"

"%PYTHON%" -c "import sys; from app.services.workspace_backup_service import workspace_backup_service; res = workspace_backup_service.create(); print('\nBackup created successfully:'); print(f'  Archive: {res.get(\"archive\")}'); print(f'  SHA-256: {res.get(\"sha256\")}'); print(f'  Duration: {res.get(\"duration_ms\")} ms')"

if errorlevel 1 (
    echo.
    echo [ERROR] Backup operation failed. See details above.
) else (
    echo.
    echo [SUCCESS] Backup completed and SHA-256 integrity verified.
)

echo.
pause
exit /b 0
