@echo off
setlocal
title DOKA AI DMS - Desktop Launcher

echo ===================================================
echo          DOKA AI DMS - DESKTOP EDITION
echo ===================================================
cd /d "%~dp0"

echo [1/2] Checking services...
call start-doka.bat

echo [2/2] Launching Desktop Window...
cd apps\desktop
if not exist "node_modules\electron" (
    echo Installing Desktop runtime dependencies...
    call npm install --no-audit --no-fund
)
npx electron .

exit /b 0
