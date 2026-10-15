$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Personal Local virtual environment not found. Run start_application.bat or follow LOCAL_TESTING_GUIDE.md first."
    exit 1
}

& $python -m pytest --cov=app --cov-report=term-missing
exit $LASTEXITCODE
