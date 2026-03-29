#!/bin/sh

echo "🚀 Starting API..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} &

echo "⏳ Waiting before admin setup..."
sleep 5

echo "👤 Creating admin..."
python -m app.scripts.create_admin || true

wait