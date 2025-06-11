#!/bin/bash
set -e

echo "Fetching secrets from Supabase Vault..."
python fetch_secrets.py

echo "Running migrations..."
python run_migrations.py

echo "Starting FastAPI app..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000