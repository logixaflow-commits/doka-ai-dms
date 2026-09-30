@echo off
setlocal
cd /d "%~dp0app"
if not exist "node_modules" npm ci
npm run dev
endlocal
