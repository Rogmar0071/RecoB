#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set; skipping Alembic migrations."
else
  echo "Running Alembic migrations..."
  alembic -c backend/alembic.ini upgrade head
fi

if [[ "$#" -eq 0 ]]; then
  exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec "$@"
