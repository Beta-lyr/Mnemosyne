#!/bin/bash
# Mnemosyne Linux/Mac Install Script
set -e

echo "=== Mnemosyne Install Script ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found. Please install Python 3.11+"
    exit 1
fi
echo "Python: $(python3 --version)"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -e ".[dev]"

# Copy environment config
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your API keys."
fi

# Install frontend dependencies
if [ -f "web/package.json" ]; then
    echo "Installing frontend dependencies..."
    cd web
    npm install
    npm run build
    cd ..
fi

echo ""
echo "=== Install Complete ==="
echo "Edit .env with your API keys, then run ./scripts/start.sh to start the service."
