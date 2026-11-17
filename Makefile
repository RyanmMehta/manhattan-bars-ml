# Nightlife Autopilot — integration Makefile. Run from the repo root.
#   make setup        install python deps (+ frontend npm ci if merged)
#   make data         build data/live_sim.db (seed 42; DATA_NIGHTS=N for quick mode)
#   make test         pipeline smoke + workstream tests + contract + e2e
#   make demo         run backend + frontend locally at DEMO_NOW
PY ?= python3
DEMO_NOW ?= 2026-11-14T23:30:00-05:00
API_PORT ?= 8000
WEB_PORT ?= 5173
DATA_NIGHTS ?=
NIGHTS_FLAG := $(if $(DATA_NIGHTS),--nights $(DATA_NIGHTS),)

.PHONY: setup launch-venues data snapshots tableau test test-smoke test-units test-contract test-e2e test-deployed demo synthetic-docs audit status clean

setup:
	$(PY) -m pip install -q -r requirements.txt -r requirements-dev.txt
	@[ ! -f backend/requirements.txt ] || $(PY) -m pip install -q -r backend/requirements.txt
	@[ ! -f recs/requirements.txt ] || $(PY) -m pip install -q -r recs/requirements.txt
	@[ ! -f frontend/package.json ] || (cd frontend && npm ci --no-audit --no-fund)

launch-venues:
	$(PY) -I scripts/build_launch_venues_full.py

# v2.2 §J: exactly this command, no -I (v2.2 §J CR-15; the Render build runs the same).
data:
	python -m simulator --seed 42 --out data/live_sim.db $(NIGHTS_FLAG)

test: test-smoke test-units test-contract test-e2e

test-smoke:
	$(PY) -I scripts/integration/pipeline_smoke.py

test-units:
	@[ ! -d recs ] || $(PY) -m pytest -q recs
	@[ ! -d backend ] || $(PY) -m pytest -q backend
	@[ ! -f frontend/package.json ] || (cd frontend && npm test --if-present)

test-contract:
	$(PY) -m pytest -q tests/contract

test-e2e:
	$(PY) -m pytest -q -s tests/e2e

# make test-deployed BASE_URL=https://x.vercel.app API_URL=https://y.onrender.com
test-deployed:
	API_URL=$(API_URL) $(PY) -m pytest -q tests/contract/test_api.py
	BASE_URL=$(BASE_URL) API_URL=$(API_URL) $(PY) -m pytest -q -s tests/e2e

demo:
	@[ -f data/live_sim.db ] || $(MAKE) data
	$(PY) -I scripts/integration/run_demo.py --api-port $(API_PORT) --web-port $(WEB_PORT) --now $(DEMO_NOW)

# v2.2 §J snapshots = recs Live Venue State at each snapshot_ts (matches the API). Run after `make data`.
snapshots:
	python -m recs snapshots --out data/synthetic_live/demo_night_snapshots.csv

tableau:
	$(PY) -I analytics/tableau/export_extracts.py
	$(PY) -I analytics/tableau/render_standin.py

synthetic-docs:
	$(PY) -I scripts/integration/consolidate_synthetic.py

audit:
	$(PY) -I scripts/integration/ownership_audit.py --out docs/workstreams/ownership_audit.md

status:
	git fetch -q origin && $(PY) -I scripts/integration/merge_status.py

clean:
	rm -f data/live_sim.db
