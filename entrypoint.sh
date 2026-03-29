#!/bin/sh

echo "🚀 Starting container..."

echo "👤 Creating admin if not exists..."
python -m app.scripts.create_admin

echo "🔥 Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}