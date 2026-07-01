#!/bin/bash
# Mnemosyne Linux/Mac Start Script
set -e

echo "=== Starting Mnemosyne ==="

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run ./scripts/install.sh first."
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start service
echo "Starting FastAPI service..."
uvicorn mnemosyne.app:app --host 0.0.0.0 --port 8080 --reload
