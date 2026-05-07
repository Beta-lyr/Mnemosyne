# Mnemosyne Windows Install Script
$ErrorActionPreference = "Stop"

Write-Host "=== Mnemosyne Install Script (Windows) ===" -ForegroundColor Cyan

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Error: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
$pyVersion = python --version 2>&1
Write-Host "Python: $pyVersion" -ForegroundColor Green

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -e ".[dev]"

# Copy environment config
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env file. Please edit it with your API keys." -ForegroundColor Green
}

# Install frontend dependencies
if (Test-Path "web/package.json") {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location web
    npm install
    npm run build
    Pop-Location
}

Write-Host ""
Write-Host "=== Install Complete ===" -ForegroundColor Green
Write-Host "Edit .env with your API keys, then run .\scripts\start.ps1 to start the service." -ForegroundColor Cyan
