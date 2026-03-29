#!/bin/sh

echo "🚀 Starting container..."

echo "👤 Creating admin if not exists..."
python create_admin.py

echo "🔥 Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}