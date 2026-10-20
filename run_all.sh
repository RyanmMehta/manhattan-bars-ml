#!/usr/bin/env bash
# Full pipeline: scrape -> database -> synthetic data -> ML evaluation.
# Usage: ./run_all.sh            (re-scrapes everything, ~10 min total)
#        SKIP_SCRAPE=1 ./run_all.sh   (reuse data/raw/)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
PY=".venv/bin/python -I"

[ "${SKIP_SCRAPE:-0}" = 1 ] || $PY src/scrape.py
$PY src/build_db.py
for m in independent copula cart; do $PY src/simulate.py --method "$m" --n 10000; done
$PY src/evaluate.py --seeds 3
