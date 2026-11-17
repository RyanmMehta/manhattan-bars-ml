# Build the Nightlife Autopilot dashboard in Tableau Public

Target: 5 sheets (S1-S5) and 1 dashboard (D1), about 30-45 min. Every hex code below
comes from `style.py`; change colours there first, then here.
The stand-in `dashboard_standin.png` shows what each sheet should look like.

## 0. Refresh the extracts (2 commands, < 10 s)
```bash
pip install -r requirements.txt -r analytics/tableau/requirements.txt
python -I analytics/tableau/export_extracts.py     # writes analytics/tableau/extracts/
python -I analytics/tableau/render_standin.py      # writes dashboard_standin.png/.pdf
```
The exporter prints `tonight_source`: `placeholder` (SYN-T1), or `live-sim` once
`data/synthetic_live/demo_night_snapshots.csv` or `data/live_sim.db` exists.

## 1. Install and connect
1. Install **Tableau Public** (free desktop app, 2025.x or newer) and sign in to your Tableau Public account.
2. Connect → **To a File → Text file** → `analytics/tableau/extracts/bars.csv`.
3. Add each of these as a **separate data source** (Data → New Data Source → Text file). Don't join them:
   - `extracts/neighborhood_summary.csv`
   - `extracts/grade_by_neighborhood.csv`
   - `extracts/launch_venues.csv`
   - `extracts/synthetic/syn_tonight_heatmap.csv`
   - (optional, for tooltips) `extracts/synthetic/syn_tonight_reports.csv`
4. Rename the sources `Bars`, `Neighborhoods`, `Grades`, `Launch`, `Tonight (DEMO)`.

## 2. Data types (each source's data pane)
| Source | Field | Set to |
|---|---|---|
| all | `venue_id`, `zip`, `osm_id` | String (Abc), Dimension |
| Bars, Launch, Tonight | `lat` | Geographic Role → Latitude |
| Bars, Launch, Tonight | `lon` | Geographic Role → Longitude |
| Bars | `complaint_bucket` | String; Default Properties → Sort → Manual: `0, 1-2, 3-9, 10-49, 50+` |
| Grades | `latest_grade` | Default Properties → Sort → by field `grade_order` (ascending) |
| Tonight | `hour_order` | Discrete Dimension (drag to Dimensions, convert to Discrete) |
| Tonight | `hour_label` | Default Properties → Sort → by field `hour_order` (Minimum, ascending) |
| Tonight | `snapshot_ts` | String (keep the ISO text; it is only for tooltips) |
| all | `is_synthetic` | Dimension |

Empty cells load as NULL. Leave them NULL; don't replace them with 0.

## 3. Sheets

### S1 Manhattan map (source `Bars`)
- Columns: `lon` (Dimension), Rows: `lat` (Dimension). Marks: Circle.
- Filters: `has_coords` = 1; `venue_type` (Show Filter, all checked).
- Colour: `complaint_bucket`. Edit colours:
  `0 #d4d3cd`, `1-2 #f3d9cc`, `3-9 #eb8a62`, `10-49 #d95926`, `50+ #9c3a14`. Border: white.
- Size: `noise_complaints` (SUM), size range small → medium.
- Detail: `venue_id`. Tooltip: `name`, `address`, `venue_type`, `latest_grade`, `noise_complaints`.
- Map → Background Maps → Light. Zoom to Manhattan and lock it (Map → Map Options → uncheck "Allow pan & zoom" if you like).
- Title: `S1  Manhattan's 1,727 licensed bars`
- Caption (Worksheet → Show Caption): **311 noise complaints = complaint risk, not nightlife quality.**

### S2 Density by neighbourhood (source `Neighborhoods`)
- Rows: `neighborhood`. Columns: SUM(`n_bars`). Marks: Bar. Sort `neighborhood` by `n_bars` descending.
- Create a calculated field `Is launch area` = `[neighborhood] = "LES/Chinatown"`.
  Colour: `Is launch area` → True `#2a78d6`, False `#c3c2b7`. Hide the colour legend.
- Label: `n_bars` and `complaints_per_bar` (format: number, 1 decimal, suffix " complaints/bar").
- Tooltip: `n_venues`, `n_bars`, `mean_density_100m`, `total_complaints`, `pct_high_noise`, `pct_grade_a`.
- Title: `S2  Bars per neighbourhood (LES/Chinatown highlighted)`. Caption: "Neighbourhood = zip-code grouping.
  311 noise complaints = complaint risk, not nightlife quality."

### S3 Health grades (source `Grades`)
- Rows: `neighborhood`. Columns: SUM(`pct`). Marks: Bar. Colour: `latest_grade`
  (`A #1baf7a`, `B #eda100`, `C #eb6834`, `N #898781`, `Z #52514e`, `Not matched #e1e0d9`).
- Axis fixed 0 to 100. Sort `neighborhood` the same as S2 (by field → `Neighborhoods`… or manual).
- Tooltip: `latest_grade`, `n`, `pct`.
- Title: `S3  Health grade mix by neighbourhood`. Caption: "'Not matched' = no DOHMH inspection match, shown, not dropped."

### S4 LES zoom (sources `Bars` + `Launch`)
- Map: duplicate S1. Filter `zip` = `10002`. Colour: `is_launch` → 1 `#2a78d6`, 0 `#c3c2b7` (opacity 60%).
  Size: fixed. Label: `name`, shown only for `is_launch` = 1 (Label → Marks to label: Selected, or put
  a calc `IF [is_launch]=1 THEN [name] END` on Label).
- Table: new sheet `S4 table` from `Launch`: Rows `launch_rank`, `name`, `venue_type`, `latest_grade`;
  Text `noise_complaints`. 35 rows.
- Title: `S4  Lower East Side (zip 10002): 35 launch venues`. Caption: complaint caption above.

### S5 Tonight heatmap (source `Tonight (DEMO)`) — synthetic
- Columns: `hour_order` (discrete), then put `hour_label` on Columns *after* it and hide the `hour_order` header.
- Rows: `name`. Sort `name` by field `vibe_score`, aggregation **Maximum**, descending.
- Marks: Square.
- Display rule (v2 §A), three calculated fields:
  - `Shown vibe` = `IF [display] = "show" THEN [vibe_score] END`
  - `Low vibe` = `IF [display] = "low" THEN [vibe_score] END`
  - `Cell text` = `IF [display] = "show" THEN STR([vibe_score]) ELSEIF [display] = "low" THEN STR([vibe_score]) + "?" END`
- Colour: `Shown vibe` → Edit Colours → Custom Sequential, start `#cde2fb`, end `#0d366b`,
  Advanced: Start 0, End 100; rename the legend "vibe_score (0-34 Chill · 35-64 Lively · 65-100 Packed)".
  Cells whose `Shown vibe` is NULL (low and none) get the null colour: Format → Shading → Pane `#f0efec`.
- Text: `Cell text` (low-confidence cells read e.g. "35?" on the pale background; "no number" = No fresh reports).
  Add a legend text box: "35? = low confidence (0.20-0.39) · blank = No fresh reports".
  (Tableau has no hatch fill; the "?" replaces the stand-in PNG's hatching. Untested in Tableau: verify while building.)
- Reference line at "now": right-click the `hour_order` = 3 header (23:30 snapshot) → Annotate → Area, text "now 23:30",
  border `#e34948`. Alternatively Highlight `is_after_demo_now` = 0 / 1 with a 2nd Colour encoding on borders.
- Tooltip:
  ```
  <name>  ·  <hour_label> (snapshot <snapshot_ts>)
  Vibe <vibe_score> (<vibe_band>)   confidence <confidence>   display <display>
  <n_reports> reports · crowd <crowd> · dancing <dancing> · line <line_minutes> min
  source: <source>  ·  DEMO DATA (synthetic)
  ```
  For `display = none`, the tooltip should read "No fresh reports": calc
  `IF [display]="none" THEN "No fresh reports" ELSE STR([vibe_score]) END`.
- Title: **`S5  Tonight (Sat Nov 14) vibe by hour — DEMO DATA (synthetic)`**, title shading `#6250d6`, font white.

## 4. Dashboard D1
1. New Dashboard → Size: Fixed, 1600 × 1000.
2. Layout (tiled): left column S1 (full height, ~30% width); top-right row S2 | S3; bottom-right row S4 | S5.
   Put `S4 table` as a floating or tabbed object under S4 if space allows.
3. Text object at the top:
   "Nightlife Autopilot: where Manhattan drinks, and why we launch on the Lower East Side.
   Public data: NY SLA liquor licences, NYC DOHMH inspections, NYC 311 noise complaints, OpenStreetMap.
   S5 only is DEMO DATA (synthetic): cell HH = Live Venue State at HH:30 on Sat Nov 14 2026; 'now' = 23:30."
4. Text badge next to S5: "DEMO DATA (synthetic)", background `#6250d6`, white bold text.
5. Optional action: Dashboard → Actions → Filter, source S2, target S1/S3, run on Select (click a neighbourhood).

## 5. Publish and save
1. File → **Save to Tableau Public As…** → name `Nightlife Autopilot — Manhattan bars`.
   Check that the sheet titles and captions show in the published view.
2. Copy the public URL into `docs/workstreams/tableau.md` ("Tableau Public link").
3. File → **Save As** → `analytics/tableau/nightlife_dashboard.twbx` (packaged, extracts travel with it). Commit it (< 10 MB).
4. Dashboard → **Export as PDF** → `analytics/tableau/dashboard_tableau.pdf`. Commit it.

## 6. Refresh when extracts change (e.g. live-sim lands)
1. Rerun the two commands in §0. Check the printed `tonight_source` is `live-sim`.
2. Tableau: Data → each source → **Refresh** (or Data → Refresh All Extracts).
3. Spot-check: S2 totals = `neighborhood_summary.csv` (e.g. LES/Chinatown 136, East Village 242, Midtown West 274).
4. Save to Tableau Public (same name overwrites), re-save `.twbx`, re-export PDF, commit the CSVs + PNG.

## Colour reference (from `style.py`)
| Use | Hex |
|---|---|
| Complaints 0 / 1-2 / 3-9 / 10-49 / 50+ | `#d4d3cd` `#f3d9cc` `#eb8a62` `#d95926` `#9c3a14` |
| Grades A / B / C / N / Z / Not matched | `#1baf7a` `#eda100` `#eb6834` `#898781` `#52514e` `#e1e0d9` |
| LES highlight / other | `#2a78d6` / `#c3c2b7` |
| Vibe ramp 0 → 100 (ticks 35, 65) | `#cde2fb` `#86b6ef` `#3987e5` `#1c5cab` `#0d366b` |
| Low confidence / no fresh reports | `#c3c2b7` (hatched) / `#f0efec` |
| DEMO_NOW outline | `#e34948` |
| Demo-data badge | `#6250d6` |
