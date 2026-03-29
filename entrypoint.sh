#!/bin/sh

echo "🚀 Starting API..."

echo "👤 Creating admin..."
python -m app.scripts.create_admin || true

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}