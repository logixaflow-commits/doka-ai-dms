@echo off
REM Enterprise AI DMS - Setup Script for Windows

echo Setting up Enterprise AI DMS environment...

REM Create .env file if it doesn't exist
if not exist "dms\.env" (
    copy "dms\.env.example" "dms\.env"
    echo Created .env file
    echo Please update dms\.env with your configuration
) else (
    echo .env file already exists
)

if not exist "app\.env.local" (
    copy "app\.env.example" "app\.env.local"
    echo Created .env.local file
    echo Please update app\.env.local with your configuration
) else (
    echo .env.local file already exists
)

REM Create directories
echo Creating necessary directories...
if not exist "storage\documents" mkdir storage\documents
if not exist "storage\versions" mkdir storage\versions
if not exist "storage\workflows" mkdir storage\workflows
if not exist "storage\reports" mkdir storage\reports
if not exist "storage\quotas" mkdir storage\quotas
if not exist "storage\usage" mkdir storage\usage
if not exist "storage\rate_limit_rules" mkdir storage\rate_limit_rules
if not exist "storage\api_usage" mkdir storage\api_usage
if not exist "storage\report_templates" mkdir storage\report_templates
if not exist "storage\report_schedules" mkdir storage\report_schedules
if not exist "storage\workflow_instances" mkdir storage\workflow_instances
if not exist "backups" mkdir backups
if not exist "logs" mkdir logs

echo Directories created

REM Install Python dependencies
echo Installing Python dependencies...
cd dms
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -r requirements-test.txt
cd ..

echo Python dependencies installed

REM Install Node.js dependencies
echo Installing Node.js dependencies...
cd app
call npm install
cd ..

cd mobile
call npm install
cd ..

echo Node.js dependencies installed

REM Initialize database
echo Initializing database...
cd dms
call venv\Scripts\activate.bat
python -c "from app.core.database import init_database; init_database()" 2>nul || echo Database initialization skipped
cd ..

echo Database initialized

REM Setup logs
echo Setting up logs...
if not exist "logs\app.log" type nul > logs\app.log
if not exist "logs\error.log" type nul > logs\error.log
if not exist "logs\access.log" type nul > logs\access.log

echo Logs directory created

echo.
echo Setup completed successfully!
echo Enterprise AI DMS is ready to use!
echo.
echo Next steps:
echo 1. Update dms\.env with your configuration
echo 2. Update app\.env.local with your configuration
echo 3. Run 'docker-compose up -d' to start services
echo 4. Or run 'cd dms && venv\Scripts\activate && uvicorn app.main:app --reload' for development

pause