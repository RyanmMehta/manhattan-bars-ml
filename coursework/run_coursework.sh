#!/usr/bin/env bash
# Run both coursework exercises end to end on CPU (about 2 minutes on a laptop).
#   pip install torch --index-url https://download.pytorch.org/whl/cpu
#   pip install -r coursework/requirements.txt
#   bash coursework/run_coursework.sh
set -euo pipefail
cd "$(dirname "$0")/.."            # repo root
PY="${PYTHON:-python}"

echo "== check dependencies"
$PY -I -c "import torch, sklearn, pandas, matplotlib; print('torch', torch.__version__, '| sklearn', sklearn.__version__)"

echo "== (a) tiny transformer"
$PY -I coursework/tiny_transformer/baselines.py
$PY -I coursework/tiny_transformer/train.py --ablation
$PY -I coursework/tiny_transformer/sample.py --n 20 --temperature 0.8 --summary

echo "== (b) churn: data"
# SYNTHETIC: Scout data comes from live-sim (data/live_sim.db). Build it with the contract command
# when the simulator exists; otherwise fall back to the marked stand-in generator.
if [ ! -f "${LIVE_SIM_DB:-data/live_sim.db}" ] && [ -f simulator/__main__.py ]; then
  $PY -m simulator --seed 42 --out data/live_sim.db   # contract command; -I would hide simulator/
fi
if [ ! -f "${LIVE_SIM_DB:-data/live_sim.db}" ]; then
  echo "data/live_sim.db not available -> using the SYNTHETIC stand-in generator"
  $PY -I coursework/churn/make_standin_data.py --seed 0
fi

echo "== (b) churn: model"
$PY -I coursework/churn/build_dataset.py
$PY -I coursework/churn/train_eval.py
$PY -I coursework/churn/explain.py
$PY -I coursework/churn/evaluate_truth.py
echo "done: see coursework/*/outputs/ and coursework/churn/outputs/report.md"
