# OUTLINE: tableau build plan

Sizes: S ≈ < 1 h, M ≈ 1-3 h, L ≈ 3-6 h (placeholders).
Order: public-data parts first (no dependencies), synthetic tonight sheet last.
Aligned with CONTRACTS.md v2 (commit 2129052). Push deadline: **Fri Nov 13 18:00 ET**;
integration merges tableau 3rd (after specs, research, before live-sim/ml-recs), so the
branch must ship working with the SYN-T1 placeholder and refresh once live-sim lands.

## 1. Ordered tasks
- [ ] T1 (S) Scaffold `analytics/tableau/` tree, `requirements.txt` (matplotlib), README stub.
- [ ] T2 (S) `style.py`: colour scales, complaint buckets (0, 1-2, 3-9, 10-49, 50+), grade colours, demo-data badge colour.
- [ ] T3 (M) `queries.py` + `export_extracts.py` for public extracts E1-E5 (§3).
- [ ] T4 (S) Tests for E1-E5 (columns, counts, determinism).
- [ ] T5 (M) Tonight extract E6: read `syn_scout_reports` from `data/live_sim.db` (path from env `LIVE_SIM_DB`) if present, rows with `status = 'accepted'` (plus `pending`, see open Q) for Sat Nov 14 20:00 → Sun Nov 15 03:00 ET; compute hourly state via `recs.live_state.compute_all` if importable, else the v2-constant fallback (§5); if the DB is absent, generate SYN-T1 placeholder.
- [ ] T6 (S) Tests for E6 (ranges, `is_synthetic`, path/name rules).
- [ ] T7 (M) `render_standin.py`: 5-panel matplotlib figure → `dashboard_standin.png` (+ `.pdf`).
- [ ] T8 (L) Build Tableau workbook: 5 sheets + dashboard, save `nightlife_dashboard.twbx`.
- [ ] T9 (M) Write `BUILD_TABLEAU.md` while building (screens/steps, shelf by shelf).
- [ ] T10 (S) Publish to Tableau Public; export dashboard PDF; record link.
- [ ] T11 (S) `docs/synthetic/tableau.md` registry + `docs/workstreams/tableau.md`.
- [ ] T12 (S) Fresh-run check: clean clone → two commands → tests pass; push branch by Fri Nov 13 18:00 ET.
- [ ] T13 (S, after live-sim + ml-recs merge, Nov 14-15) Rerun exporter against `data/live_sim.db` + real `recs`, refresh + republish Tableau, re-render PNG; `source` column flips `placeholder` → `live-sim`.

Total ≈ 14-20 h.

## 2. File tree to be created
```
analytics/tableau/
  README.md                  # 10-line how-to-run
  requirements.txt           # matplotlib>=3.9, pytest>=8
  style.py                   # colours, buckets, labels (single source)
  queries.py                 # SQL per extract
  export_extracts.py         # manhattan_bars.db (+ live_sim.db) -> extracts/
  render_standin.py          # extracts -> dashboard_standin.png/.pdf
  BUILD_TABLEAU.md           # step-by-step Tableau Public instructions
  nightlife_dashboard.twbx   # packaged workbook (binary)
  dashboard_standin.png
  dashboard_tableau.pdf      # export from Tableau after publish
  extracts/
    bars.csv
    venue_features_slim.csv
    launch_venues.csv
    neighborhood_summary.csv
    grade_by_neighborhood.csv
    synthetic/
      syn_tonight_heatmap.csv
      syn_tonight_reports.csv     # copy/subset of live-sim reports for tooltips
  tests/
    test_extracts.py
    test_synthetic.py
    test_render.py
docs/synthetic/tableau.md
docs/workstreams/tableau.md
```

## 3. Extracts (CSV, all with `is_synthetic`)
| ID | File | Source | Rows | Columns |
|---|---|---|---|---|
| E1 | `bars.csv` | `v_bars` LEFT JOIN `venue_features` | 1,727 | venue_id, name, address, zip, neighborhood, lat, lon, has_coords, venue_type, liquor_tier, latest_grade (NULL→`Not matched`), noise_complaints, complaint_bucket, high_noise, density_100m, density_250m, years_licensed, osm_amenity, osm_closes_late, is_launch, is_synthetic=0 |
| E2 | `venue_features_slim.csv` | `venue_features` (all 5,704) | 5,704 | venue_id, venue_type, neighborhood, latest_grade, lat, lon, noise_complaints, high_noise, density_100m, mean_score, is_synthetic=0 |
| E3 | `launch_venues.csv` | `data/launch_venues.csv` (header `license_id`, aliased `AS venue_id`) + E1 fields | 35 | venue_id, name, address, lat, lon, venue_type, latest_grade, noise_complaints, osm_id, launch_rank, is_synthetic=0 |
| E4 | `neighborhood_summary.csv` | `venues` + `v_bars` grouped | 15 | neighborhood, n_venues, n_bars, n_clubs, mean_density_100m, total_complaints, complaints_per_bar, pct_high_noise, pct_grade_a, centroid_lat, centroid_lon, is_synthetic=0 |
| E5 | `grade_by_neighborhood.csv` | E1 grouped | ~90 | neighborhood, latest_grade, n, pct, is_synthetic=0 |
| E6 | `synthetic/syn_tonight_heatmap.csv` | live-sim reports → hourly state (shape = `/api/heatmap?by=hour` item + extras) | 35 × 8 = 280 | venue_id, name, lat, lon, night_date (2026-11-14), hour (20-03), hour_order, hour_label, vibe_score (nullable), confidence (nullable), display (show/low/none), n_reports, crowd, line_minutes, trend, is_after_demo_now, source (`live-sim`/`placeholder`), is_synthetic=1 |
| E7 | `synthetic/syn_tonight_reports.csv` | live-sim `syn_scout_reports` filtered to launch venues + Sat Nov 14 night | ~500 (placeholder) | v2 `syn_scout_reports` columns unchanged (incl. `status`, `distance_m`) |

Notes: 18 `v_bars` rows have no coordinates/features; keep them in E1 with
`has_coords=0`, exclude from map sheets with a filter. Hours after midnight
belong to the previous `night_date` (hour order 20,21,22,23,0,1,2,3 via `hour_order`).
Each hourly cell is the Live Venue State at `now = HH:00 + 59 min` (end of the hour).
DEMO_NOW = 2026-11-14T23:30-05:00: the full night is shown (it is replayed history),
but cells after DEMO_NOW get `is_after_demo_now = 1` and a dashed reference line at 23:30
so the demo can say "this is now". Never read `syn_true_state`/`syn_scout_truth`
(evaluation-only tables).

## 4. Dashboard sheets
| Sheet | Extract | Viz | Key settings |
|---|---|---|---|
| S1 Manhattan map | E1 | symbol map | lat/lon roles; colour = complaint_bucket; size = noise_complaints (log); filter has_coords=1, venue_type; caption on complaint risk |
| S2 Density by neighbourhood | E4 | horizontal bar | n_bars desc; colour highlight LES/Chinatown; label complaints_per_bar |
| S3 Health grades | E5 | 100% stacked bar | colour by grade (A green, B yellow, C orange, N/Z grey, Not matched light grey) |
| S4 LES zoom | E1 + E3 | map + table | zip=10002; launch venues bold/labelled; others faded; table of 35 |
| S5 Tonight heatmap (DEMO DATA) | E6 | highlight table | title "Sat Nov 14 — DEMO DATA (synthetic)"; rows venue (sorted by peak vibe), cols hour_order, colour vibe_score 0-100 sequential; v2 display rule: `display=low` (conf 0.20-0.39) cells hatched/greyed, `none` (< 0.20 or null) blank with "No fresh reports" tooltip; tooltip n_reports, confidence, trend; reference line at 23:30 (DEMO_NOW) |
| D1 Dashboard | all | 2×3 grid | S1, S2, S3, S4, S5 + text box (sources, date, synthetic note); fixed size 1600×1000 |

Stand-in PNG mirrors S1-S5 with matplotlib (scatter on lat/lon with equal aspect ≈ cos(40.75°), barh, stacked barh, LES scatter + labels, imshow heatmap).

## 5. Interfaces
Consumed (per CONTRACTS.md):
- `data/manhattan_bars.db` tables `v_bars`, `venues`, `venue_features` (read-only).
- `data/launch_venues.csv` (venue_id = license_id).
- live-sim: `data/live_sim.db` (env `LIVE_SIM_DB`; generated, seed 42, not committed) tables `syn_scout_reports` (+ optional `syn_venue_updates`, `syn_scouts.reputation` joined as `reputation`, default 0.5) per v2 §E.
- ml-recs: `recs.live_state.compute_all(reports, updates, now) -> list[dict]` (Live Venue State incl. optional `display`, nullable `vibe_score`/`confidence`/`trend`), called at each hour end on Sat Nov 14.
- Later backend: `GET /api/heatmap?now=&by=hour` → `{venue_id, lat, lon, hour, vibe_score, confidence, n_reports, is_synthetic}` (v2 §G; accepted CCR). With `INCLUDE_SYNTHETIC=0` it serves only real `scout_reports`.

Provided:
- CSV extracts (§3) — other workstreams may read but not edit.
- `dashboard_standin.png`, `dashboard_tableau.pdf`, Tableau Public URL.
- `style.py` colour scales (frontend can mirror hex codes).

Fallback state (only if `recs` is not importable), marked `# SYNTHETIC: replace with recs.live_state`,
using v2 §A constants: reports with age ≤ 180 min and ts ≤ now+2 min; weight
`w = 0.5 ** (age_min / 30) · (0.25 + 0.75·reputation) · (1 if verified_presence else 0.6)`;
`vibe = 100 · weighted mean of (0.5·(crowd-1)/4 + 0.5·dancing/2)` (simplified until
`docs/specs/SCORING.md` exists — the build session must copy the specs formula and pass
golden vector G1: vibe 65 / conf 0.67); `confidence = 1 - exp(-Σw / 1.5)`; display per
threshold (≥ 0.40 show, 0.20-0.39 low, else none). Null vibe/confidence if no reports.

## 6. Synthetic datasets needed
**SYN-T1 `syn_tonight_reports.csv` placeholder** (only when `data/live_sim.db` is missing)
- Imitates: scout vibe checks at the 35 launch venues on Sat Nov 14 2026, 20:00-03:00 ET.
- Generate: in `export_extracts.py --placeholder`, seed 42; per venue a peak hour
  drawn from {22,23,0,1} (all launch venues are Bar/Tavern per v2 §D), Poisson report count per hour with mean
  2 × bell curve around peak; crowd ~ clip(round(N(1+4·curve, 0.7)),1,5);
  dancing mostly 0, 1-2 only at crowd ≥ 4 for ~20% of venues (sparse, mirrors `has_dance_floor`);
  line_minutes ~ round(Gamma) when crowd ≥ 4 else 0; cover_usd/music_genre null;
  `status='accepted'`, `distance_m` null; ids `syn-r-T1-000001`, scout `syn-s-T1-0001` (T1 marks the
  placeholder so ids never collide with live-sim's `syn-r-…`); `is_synthetic=1`.
- Real replacement: live-sim `data/live_sim.db` `syn_scout_reports` (first), then real
  `scout_reports` (backend, `INCLUDE_SYNTHETIC=0`).
- Swap: generate `data/live_sim.db` (live-sim CLI, seed 42) or set `LIVE_SIM_DB` → rerun exporter
  (`source` changes to `live-sim`) → Tableau Data → Refresh → republish → re-render PNG.

**SYN-T2 `syn_tonight_heatmap.csv`** (derived)
- Imitates: hourly Live Venue State per launch venue.
- Generate: from SYN-T1 or live-sim reports via `recs.live_state.compute_all` (or fallback).
- Real replacement: `GET /api/heatmap?now=…&by=hour` from backend over real reports.
- Swap: exporter `--tonight-source api --base-url … --now 2026-11-14T23:30:00-05:00` calls `GET /api/heatmap?by=hour`; same output columns; refresh + republish.

Both listed in `docs/synthetic/tableau.md` with commands and seeds.

## 7. Test plan
- Unit (pytest): see RULES.md list — schema, counts, joins, synthetic marking, value ranges, determinism, PNG size.
- Cross-check: `SELECT COUNT(*) FROM v_bars WHERE zip='10002'` = 136 equals E1 zip-10002 count; E4 total n_bars = 1,727.
- Visual review checklist (manual, in `docs/workstreams/tableau.md`): every synthetic panel has the badge; complaint caption present; LES highlighted; legends readable at 1920 px.
- Tableau: after Data → Refresh, sheet totals match E4 (spot-check 3 neighbourhoods).

## 8. Demo script (≈ 2 min)
1. Open the Tableau Public link (fallback: `dashboard_standin.png`).
2. S1: "1,727 licensed bars in Manhattan from SLA + OSM; colour is 311 noise complaints — complaint risk, not quality."
3. S2: "Midtown West and East Village lead on count; LES/Chinatown is dense with high complaints per bar — a busy, contested night scene." (quote E4 numbers)
4. S3: "Health grades are mostly A; ~22% of bars have no DOHMH match — shown, not hidden." (placeholder %)
5. S4: zoom to 10002: "Our 35 launch venues, e.g. Attaboy, Mr. Fong's, Mehanata."
6. S5: "DEMO DATA: simulated Saturday Nov 14. The line marks 23:30, the demo's 'now'. Energy builds after 22:00 and peaks around midnight-1am; grey cells are low confidence, blank cells have no fresh reports. This is what the app's live vibe score shows."
7. Close: "Rerun two commands to refresh; synthetic files swap for real reports with no sheet changes."

## 9. Build-instructions outline (`BUILD_TABLEAU.md`)
1. Install Tableau Public Desktop; sign in.
2. Connect → Text file → `extracts/bars.csv`; add other CSVs as separate data sources (no joins; use blending on `venue_id`/`neighborhood`).
3. Set `lat`/`lon` geographic roles; `zip` as string; `hour_order` as discrete dimension.
4. Build S1-S5 shelf by shelf (exact pills, colours from `style.py`, filters, tooltips, titles).
5. Dashboard D1: fixed 1600×1000, layout grid, text box with sources and synthetic note.
6. File → Save to Tableau Public; then File → Save As `.twbx` into `analytics/tableau/`; Dashboard → Export PDF.
7. Refresh procedure when extracts change.
