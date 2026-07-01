# Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ .
RUN npm run build

# Python backend
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata + source for pip install
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy remaining config and frontend build
COPY alembic.ini .
COPY --from=frontend /app/web/dist web/dist/

RUN mkdir -p uploads

EXPOSE 8080

CMD ["uvicorn", "mnemosyne.app:app", "--host", "0.0.0.0", "--port", "8080"]
