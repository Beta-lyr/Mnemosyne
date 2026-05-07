# Mnemosyne Windows Start Script
$ErrorActionPreference = "Stop"

Write-Host "=== Starting Mnemosyne ===" -ForegroundColor Cyan

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Error: Virtual environment not found. Run .\scripts\install.ps1 first." -ForegroundColor Red
    exit 1
}

# Run database migrations
Write-Host "Running database migrations..." -ForegroundColor Yellow
alembic upgrade head

# Start service
Write-Host "Starting FastAPI service..." -ForegroundColor Green
uvicorn mnemosyne.app:app --host 0.0.0.0 --port 8080 --reload
