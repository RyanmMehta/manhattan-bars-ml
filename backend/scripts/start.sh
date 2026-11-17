#!/usr/bin/env bash
# Boot: migrate -> check live_sim.db -> uvicorn. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
alembic upgrade head
python scripts/ensure_sim.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
