@echo off
REM Enterprise DMS - Local Test Runner
REM This script runs the test suite locally

echo ========================================
echo Enterprise DMS - Local Test Runner
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found at venv\Scripts\activate.bat
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

echo.
echo Installing test dependencies...
pip install pytest pytest-cov pytest-mock -q

echo.
echo ========================================
echo Running Tests
echo ========================================
echo.

REM Set environment variable to skip config validation during tests
set SKIP_CONFIG_VALIDATION=true

REM Run the tests
cd /d "%~dp0"
python -m pytest tests/test_security.py tests/test_health_check.py -v --tb=short

echo.
echo ========================================
echo Test Run Complete
echo ========================================
echo.

REM Keep window open for review
pause
