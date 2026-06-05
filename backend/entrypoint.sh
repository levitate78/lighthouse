#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Gunicorn..."
exec gunicorn \
  --log-devel debug \
  --workers 2 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app