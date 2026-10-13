@echo off
setlocal EnableExtensions
title Doka AI DMS - Shutdown

echo ===================================================
echo          STOPPING DOKA AI DMS SERVICES
echo ===================================================

powershell -Command "Get-NetTCPConnection -LocalPort 8000, 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo.
echo All Doka AI DMS backend and frontend services have been stopped.
echo.
timeout /t 2 /nobreak >nul
exit /b 0
