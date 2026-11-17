#!/usr/bin/env bash
# Wake the Render backend before class and keep it warm.
# Usage: API_URL=https://<backend>.onrender.com scripts/integration/warmup.sh [--loop]
set -euo pipefail
API_URL="${API_URL:?set API_URL}"
NOW="${DEMO_NOW:-2026-11-14T23:30:00-05:00}"
ping_once() {
  date
  curl -fsS --max-time 90 "$API_URL/api/health" && echo
  curl -fsS --max-time 60 -o /dev/null -w "recommend %{http_code} %{time_total}s\n" \
    -H 'Content-Type: application/json' -X POST "$API_URL/api/recommend?now=$NOW" \
    -d '{"genres":["hip-hop","r&b"],"want_dancing":true,"crowd_pref":4,"max_cover_usd":20,"max_line_minutes":15,"max_distance_km":1.5,"lat":40.7203,"lon":-73.9881,"group_size":4}'
}
ping_once
if [ "${1:-}" = "--loop" ]; then while sleep 600; do ping_once || true; done; fi
