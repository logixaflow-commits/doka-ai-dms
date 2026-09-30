# Enterprise DMS - Local Test Runner (PowerShell)
# This script runs the test suite locally

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Enterprise DMS - Local Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
$venvPath = ".\venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Virtual environment created." -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install test dependencies
Write-Host ""
Write-Host "Installing test dependencies..." -ForegroundColor Yellow
pip install pytest pytest-cov pytest-mock -q

# Set environment variable
$env:SKIP_CONFIG_VALIDATION = "true"

# Run tests
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

cd dms
pytest tests/test_security.py tests/test_health_check.py -v --tb=short

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Run Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Keep window open
Read-Host "Press Enter to exit"
