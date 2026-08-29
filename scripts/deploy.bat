@echo off
REM Enterprise AI DMS - Automated Deployment Script for Windows

echo Starting Enterprise AI DMS Deployment...

set PROJECT_DIR=%~dp0
set BACKUP_DIR=%PROJECT_DIR%backups
set LOG_FILE=%PROJECT_DIR%deployment.log

echo [%date% %time%] Starting deployment process... >> %LOG_FILE%

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup existing data
echo Creating backup of existing data...
docker exec postgres pg_dump dms > "%BACKUP_DIR%\database_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql" 2>nul
echo Database backup created

if exist "storage" (
    REM Use PowerShell for compression
    powershell -Command "Compress-Archive -Path storage -DestinationPath '%BACKUP_DIR%\storage_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.zip'"
    echo Storage backup created
)

REM Stop existing services
echo Stopping existing services...
docker-compose -f docker-compose.production.yml down
echo Services stopped

REM Pull latest images
echo Pulling latest Docker images...
docker-compose -f docker-compose.production.yml pull
echo Docker images pulled

REM Build images
echo Building Docker images...
docker-compose -f docker-compose.production.yml build
echo Docker images built

REM Start services
echo Starting services...
docker-compose -f docker-compose.production.yml up -d
echo Services started

REM Wait for services
echo Waiting for services to be healthy...
timeout /t 30 /nobreak

REM Run migrations
echo Running database migrations...
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
echo Database migrations completed

REM Initialize database
echo Initializing database...
docker-compose -f docker-compose.production.yml exec backend python -c "from app.core.database import init_database; init_database()"
echo Database initialized

REM Check status
echo Checking services status...
docker-compose -f docker-compose.production.yml ps
echo Services status checked

echo.
echo Deployment completed successfully!
echo Enterprise AI DMS is now running!
echo Access the application at: http://localhost:3000
echo API documentation at: http://localhost:8000/docs

pause