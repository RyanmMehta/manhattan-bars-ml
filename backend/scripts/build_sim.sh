#!/usr/bin/env bash
# Build data/live_sim.db at BUILD time (v2 §J). Run from the repo root.
# SYNTHETIC: live-sim's simulator output; replaced by real tables (INCLUDE_SYNTHETIC=0).
set -euo pipefail
OUT="${LIVE_SIM_DB:-data/live_sim.db}"
if [ ! -f simulator/__main__.py ]; then
  echo "build_sim: simulator/ not present (live-sim not merged yet); skipping" >&2
  exit 0
fi
# Contract command first. `python -I` drops the cwd from sys.path, so it only works once
# simulator is installed; fall back to the same command without -I (CR-15).
python -I -m simulator --seed 42 --out "$OUT" "$@" \
  || python -m simulator --seed 42 --out "$OUT" "$@"
ls -la "$OUT"
