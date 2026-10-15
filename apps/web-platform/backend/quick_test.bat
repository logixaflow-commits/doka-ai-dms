@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: Personal Local virtual environment not found.
  echo Run start_application.bat or follow LOCAL_TESTING_GUIDE.md first.
  exit /b 1
)

"%PYTHON%" -m pytest ..\tests\test_personal_local_entrypoint.py -q
exit /b %errorlevel%
