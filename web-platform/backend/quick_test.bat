@echo off
REM Quick Test Setup - Verify environment is ready for testing
echo ========================================
echo Quick Environment Check
echo ========================================
echo.

echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python not found or not in PATH
    pause
    exit /b 1
)
echo.

echo Checking pip...
python -m pip --version
if errorlevel 1 (
    echo ERROR: pip not found
    pause
    exit /b 1
)
echo.

echo Checking pytest...
python -m pytest --version
if errorlevel 1 (
    echo Installing pytest...
    python -m pip install pytest -q
    echo pytest installed successfully.
) else (
    echo pytest is already installed.
)
echo.

echo Checking project structure...
if exist "tests\test_security.py" (
    echo [OK] test_security.py found
) else (
    echo [ERROR] test_security.py not found
)

if exist "tests\test_health_check.py" (
    echo [OK] test_health_check.py found
) else (
    echo [ERROR] test_health_check.py not found
)

if exist "tests\conftest.py" (
    echo [OK] conftest.py found
) else (
    echo [ERROR] conftest.py not found
)

if exist "pytest.ini" (
    echo [OK] pytest.ini found
) else (
    echo [ERROR] pytest.ini not found
)
echo.

echo Setting test environment variable...
set SKIP_CONFIG_VALIDATION=true
echo Environment variable set.
echo.

echo ========================================
echo Running Quick Test
echo ========================================
echo.

cd /d "%~dp0"
python -m pytest tests/test_health_check.py::TestHealthCheckImplementation::test_health_check_file_created -v

if errorlevel 1 (
    echo.
    echo ========================================
    echo Quick Test Failed
    echo ========================================
    echo Please check the errors above.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo Quick Test Passed!
    echo ========================================
    echo Your environment is ready for testing.
    echo.
    echo To run all tests, use: run_tests.bat
    echo Or manually: pytest tests/ -v
    echo.
    pause
)
