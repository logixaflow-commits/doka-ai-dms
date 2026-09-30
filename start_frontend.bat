@echo off
setlocal
cd /d "%~dp0web-platform\frontend"
if not exist "node_modules" npm ci
npm run dev
endlocal
