# analytics/tableau — Tableau extracts and stand-in dashboard

```bash
pip install -r requirements.txt -r analytics/tableau/requirements.txt
python -I analytics/tableau/export_extracts.py   # DB -> extracts/*.csv (+ extracts/synthetic/syn_*.csv)
python -I analytics/tableau/render_standin.py    # extracts -> dashboard_standin.png + .pdf
python -m pytest -q analytics/tableau/tests      # validation
```

- `extracts/` = public data (`is_synthetic=0`); `extracts/synthetic/` = demo data (`is_synthetic=1`).
- Tonight heatmap source: `data/synthetic_live/demo_night_snapshots.csv` → `data/live_sim.db` (`LIVE_SIM_DB`) → SYN-T1 placeholder (seed 42). `--placeholder` forces the placeholder.
- Rebuild in Tableau Public: `BUILD_TABLEAU.md`. Colours: `style.py`. SQL: `queries.py`.
- Synthetic registry: `docs/synthetic/tableau.md`. As-built notes: `docs/workstreams/tableau.md`.
