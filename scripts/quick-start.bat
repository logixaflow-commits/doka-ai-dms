@echo off
REM Enterprise AI DMS - Quick Start Script for Windows

echo Quick Start Enterprise AI DMS...

REM Start services with Docker Compose
echo Starting services...
docker-compose up -d

echo Waiting for services to start...
timeout /t 10 /nobreak

echo Checking service status...
docker-compose ps

echo.
echo Services started successfully!
echo.
echo Access the application:
echo   Frontend: http://localhost:3000
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Grafana: http://localhost:3001 (admin/admin123)
echo.
echo To stop services: docker-compose down
echo To view logs: docker-compose logs -f

pause