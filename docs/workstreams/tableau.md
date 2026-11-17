# Workstream: tableau (as built, Nov 17 2026)

Owner: Ryan Mehta. Branch `nightlife/tableau` (not merged to main; no PR).
Contract: `docs/CONTRACTS.md` final b46d75f (v2 amendments + §J).
Plan: `docs/prd/tableau/` (PRD, RULES, OUTLINE).

## What was built
| Item | Path | Status |
|---|---|---|
| Exporter (E1-E7) | `analytics/tableau/export_extracts.py`, SQL in `queries.py` | done, < 1 s |
| Colour/bucket/label source of truth | `analytics/tableau/style.py` | done |
| Public extracts | `analytics/tableau/extracts/{bars,venue_features_slim,launch_venues,neighborhood_summary,grade_by_neighborhood}.csv` | done (1,727 / 5,704 / 35 / 15 / 90 rows) |
| Synthetic extracts | `analytics/tableau/extracts/synthetic/syn_tonight_{heatmap,reports}.csv` | done on the SYN-T1 placeholder (245 / 523 rows) |
| Stand-in dashboard | `analytics/tableau/dashboard_standin.png` (3600×2400) + `dashboard_standin.pdf` | done, 5 panels S1-S5 |
| Tableau build steps | `analytics/tableau/BUILD_TABLEAU.md` | done |
| Tests | `analytics/tableau/tests/` (13 tests) | passing |
| Synthetic registry | `docs/synthetic/tableau.md` | done |
| Tableau workbook `.twbx`, Tableau Public link, `dashboard_tableau.pdf` | — | **not done**: no Tableau here; Ryan builds from BUILD_TABLEAU.md |

## How to run
```bash
pip install -r requirements.txt -r analytics/tableau/requirements.txt
python -I analytics/tableau/export_extracts.py
python -I analytics/tableau/render_standin.py
python -m pytest -q analytics/tableau/tests
```
Then follow `analytics/tableau/BUILD_TABLEAU.md` in Tableau Public.

Tableau Public link: _(add here after publishing)_

## Numbers the dashboard shows (public data)
- 1,727 licensed bars in `v_bars` (18 without coordinates, 19 geocoded outside the Manhattan map window).
- Most bars: Midtown West 274, East Village 242, Chelsea 189. LES/Chinatown has 136 bars and the highest
  complaints per bar (14.2, vs 7.9 East Village, 2.1 Midtown West): a dense, contested night scene.
- 23% of bars have no DOHMH inspection match ("Not matched"), shown, not dropped.
- Zip 10002: 136 bars, 35 launch venues.

## Tonight sheet (S5) status
- `origin/nightlife/live-sim` (b94468f, checked Nov 17) has no `data/synthetic_live/demo_night_snapshots.csv`
  and no `simulator/` code yet, so S5 runs on the SYN-T1 placeholder (`source = placeholder`).
- The exporter picks up the snapshot CSV automatically once it exists (HH:30 rows only), then
  `data/live_sim.db` (env `LIVE_SIM_DB`), then the placeholder. Refresh = rerun the two commands
  (BUILD_TABLEAU.md §6). The snapshot reader is unit-tested on a live-sim-shaped file.
- `recs` (ml-recs) is not on this branch; the exporter tries `recs.live_state.compute_all` and
  otherwise uses a local copy of the specs formulas (`fallback_state`, passes golden vector G1).

## Assumptions (recorded per build instructions)
1. Tableau Public and an account are not available in this session: shipped CSVs + Python stand-in PNG/PDF +
   BUILD_TABLEAU.md instead of `.twbx`, public link and Tableau PDF.
2. Placeholder report rate raised from the OUTLINE's 2 to **4 reports/hour at peak** (× venue popularity
   0.6-1.4). At 2/h only 25 of 245 cells cleared the 0.40 display threshold, which made the demo grid mostly
   blank. Now: 87 show, 60 low, 98 none. Still clearly a placeholder.
3. Placeholder scouts all have reputation 0.5 (new-scout default, v2 §A); no reputation history exists for them.
4. Heatmap counts `accepted` + `pending` reports (what the app shows live); flagged/removed weight 0, disputed 0.5 (specs §5.3).
5. Vibe/confidence formulas taken from `docs/prd/specs/PRD.md` §5.2-5.6 on `origin/nightlife/specs`
   (`docs/specs/SCORING.md` does not exist yet). Field-weight floor 0.30 applied.
6. Grade `NULL` or the string `'None'` in `venue_features.latest_grade` both map to "Not matched".
7. `launch_rank` = row order of `data/launch_venues.csv`.
8. `grade_by_neighborhood.csv` gains a `grade_order` column (for Tableau sort); `pct` sums to 100 per neighbourhood.
9. Colours follow the dataviz reference palette (blue vibe ramp, single-hue orange complaints); no frontend palette
   was published to reuse.
10. The S5 Tableau low-confidence treatment ("35?" text instead of hatching) is untested in Tableau.

## Known issues / later
- `.twbx`, Tableau Public publish, Tableau PDF export: Ryan (BUILD_TABLEAU.md §5).
- T13: rerun after live-sim pushes `demo_night_snapshots.csv` / generator; re-render PNG; republish.
- Exporter `--tonight-source api` (GET `/api/heatmap?by=hour`) not built yet (SYN-T2 real-data swap).
- S4 labels overlap in the densest blocks of the stand-in PNG; the Tableau sheet's hover tooltips avoid this.
- The manual visual checklist: every synthetic panel has the badge ✔, complaint caption on S1/S2 (the complaint-coloured panels) ✔,
  LES highlighted ✔, legible at 1920 px ✔ (reviewed by the build session, not a second person).

## Contract change requests
None.
