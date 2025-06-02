#!/bin/bash
set -e

echo "Running migrations..."
python3 run_migrations.py

echo "Starting FastAPI app..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000