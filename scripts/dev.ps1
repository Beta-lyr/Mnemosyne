# Mnemosyne Dev Mode Script
$ErrorActionPreference = "Stop"

Write-Host "=== Mnemosyne Dev Mode ===" -ForegroundColor Cyan

# Check virtual environment
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "First run, installing dependencies..." -ForegroundColor Yellow
    python -m venv .venv
    . .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev]"
    Write-Host "Dependencies installed" -ForegroundColor Green
} else {
    . .\.venv\Scripts\Activate.ps1
}

# Ensure PostgreSQL and Redis are running in Docker
Write-Host "Starting Docker services..." -ForegroundColor Yellow
docker compose up -d postgres redis

# Wait for PostgreSQL
Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Run database migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
$env:DATABASE_URL = "postgresql://mnemosyne:password@localhost:5432/mnemosyne"
alembic upgrade head

# Create uploads directory
if (-not (Test-Path "uploads")) {
    New-Item -ItemType Directory -Path "uploads" | Out-Null
}

# Load .env file
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.+)$") {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

# Start backend with hot reload
Write-Host ""
Write-Host "Starting backend (http://localhost:8080)..." -ForegroundColor Green
Write-Host "Code changes will auto-reload" -ForegroundColor Gray
Write-Host ""

uvicorn mnemosyne.app:app --host 0.0.0.0 --port 8080 --reload --reload-dir src --reload-include .env
