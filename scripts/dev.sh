#!/bin/bash
# Mnemosyne Dev Mode Script
set -e

echo "=== Mnemosyne Dev Mode ==="

# Check virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo "First run, installing dependencies..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    echo "Dependencies installed"
else
    source .venv/bin/activate
fi

# Ensure PostgreSQL and Redis are running in Docker
echo "Starting Docker services..."
docker compose up -d postgres redis

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
sleep 3

# Run database migrations
export DATABASE_URL="postgresql://mnemosyne:password@localhost:5432/mnemosyne"
echo "Running migrations..."
alembic upgrade head

# Create uploads directory
mkdir -p uploads

# Load .env
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Start backend with hot reload
echo ""
echo "Starting backend (http://localhost:8080)..."
echo "Code changes will auto-reload"
echo ""

uvicorn mnemosyne.app:app --host 0.0.0.0 --port 8080 --reload --reload-dir src --reload-include .env
