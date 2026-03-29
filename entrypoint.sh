#!/bin/sh

echo "🚀 Starting API..."

# sobe admin antes (rápido)
echo "👤 Creating admin..."
python -m app.scripts.create_admin || true

# inicia API como processo principal
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}