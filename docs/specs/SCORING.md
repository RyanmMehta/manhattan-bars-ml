# SCORING — live state, vibe, confidence, match, ranking

Purpose: the exact formulas ml-recs (`recs.live_state`, `recs.scoring`, `recs.routing`) and backend implement.
Status: agreed (Contracts v2 §A + §J; all constants are placeholders, see [PARAMETERS.md](PARAMETERS.md)).
Last updated: 2026-11-17

Test oracle: [`tools/reference_scoring.py`](tools/reference_scoring.py) translates every
formula below line by line (stdlib only, not imported by the app).
Golden vectors: [`golden_vectors.json`](golden_vectors.json) (bundle) and
[`golden_synthetic/`](golden_synthetic/) (one file per vector). See §11.

## 0. Conventions
- `now` = request time, or the `now=` replay value (demo default `DEMO_NOW = 2026-11-14T23:30:00-05:00`).
- `age_i` = minutes from input *i*'s `ts` to `now` (float, may be slightly negative).
- Compute on **unrounded** values; round only when writing an output field:
  `vibe_score` integer, `confidence` 2 dp, `crowd`/`dancing` 1 dp, `line_minutes`/`cover_usd`
  integer, `distance_km` 2 dp, `match_score` integer, `rank_score` 1 dp.
- Rounding is half away from zero. Goldens contain no value on an exact tie, so Python's
  `round()` also reproduces them.
- Missing stays `null`. Never fill a missing field with a favourable default.
- Parameter names (`H_crowd_min`, …) refer to the JSON block in PARAMETERS.md.

## 1. Eligibility
```
status weight w_status: accepted 1.0 · pending 1.0 · disputed w_disputed · flagged 0 · removed 0
missing status → treat as "accepted"
ignore input if age < −future_skew_min  or  age > cutoff_age_min
ignore scout report if w_status = 0
operator updates supply only: cover_usd, genres, dj, event, offer   (never crowd/dancing/line)
```
Report rows carry `reputation` (backend joins from `syn_scouts`/`scouts`; default `rep_new_scout`).
Replays of past nights use `syn_scout_reputation_history` as of the report date (never final reputation).

## 2. Weights
```
w_time(age, H) = 0.5 ** (max(age, 0) / H)
H by field: crowd, dancing, line_minutes        → H_crowd_min
            scout cover_usd, music_genre        → H_scout_cover_genre_min
            operator cover_usd, genres, dj      → H_operator_min
w_rep    = rep_base + rep_slope · r            (r = reputation, null → rep_new_scout)
w_ver    = 1.0 if verified_presence = 1 else w_unverified
scout    w_i,f = w_time(age_i, H_f) · w_rep · w_ver · w_status
operator w_i,f = w_time(age_i, H_operator_min) · w_operator
```
Offers (not part of Live State): active while `now < offer_expires_at`; without an expiry,
while `age ≤ H_operator_min`. Backend lists active offers on the venue detail.

## 3. Field estimates (Live Venue State)
For each field use only eligible inputs where the field is non-null. `W_f` = sum of their weights.
```
if W_f < min_field_weight: field = null
crowd        = Σ w·x / Σ w                      (scout only)          → 1 dp
dancing      = Σ w·x / Σ w                      (scout only)          → 1 dp
line_minutes = weighted_median(x, w)            (scout only)          → int
cover_usd    = weighted_median(x, w)            (scout + operator)    → int
music_genres : votes[g] += w for the scout's music_genre, and for EVERY genre in an
               operator update's pipe-separated `genres` (full weight each);
               share[g] = votes[g] / W_f;  keep g with share ≥ genre_share_min,
               sorted by share desc then slug; [] if none clears; null if W_f thin
weighted_median = sort by value; the first value whose cumulative weight ≥ W_f / 2
freshness_minutes = floor(min age over all eligible inputs (scout or operator)); null if none
n_reports    = count of eligible scout reports
sources      = ["scout"] if any eligible report, then "venue_update" if any eligible update
is_synthetic = true if any eligible input has is_synthetic = 1
```

## 4. Vibe score (0–100, current energy, not quality)
```
if crowd is null: vibe_score = null
crowd_n = (crowd − 1) / 4
dance_n = dancing / 2                                   (term dropped if dancing null)
line_n  = min(line_minutes, line_cap_min) / line_cap_min (term dropped if line null)
vibe    = 100 · Σ a_k·x_k / Σ a_k   over present terms,
          a = {crowd: vibe_w_crowd, dance: vibe_w_dance, line: vibe_w_line}
```
Use unrounded `crowd`/`dancing` (G1 gives 65 unrounded; 66 if you use the rounded 3.8/1.5).

## 5. Confidence (0–1, separate from vibe) and display
```
pairs   = (crowd, w) over eligible scout reports, w with H_crowd_min (before the W_f cutoff)
if pairs is empty:
    if eligible operator updates: conf = min(operator_conf_cap, operator_conf_cap · Σ w_operator_i)
    else:                         conf = 0.0
else:
    W       = Σ w
    support = 1 − exp(−W / conf_k)
    sd_w    = sqrt(Σ w·(x − mean)² / Σ w)           (weighted population sd)
    agree   = 1 − agree_penalty · min(1, sd_w / agree_sd_scale)
    diverse = 1.0 if ≥ 2 distinct scout_id, else diverse_single_scout
    conf    = support · agree · diverse
confidence = round(conf, 2)
```
`display` (returned in Live State, Contracts v2 §F):

| Condition | `display` | Frontend shows |
|---|---|---|
| vibe non-null and conf ≥ `display_show_min` (0.40) | `show` | vibe number + label + "N reports, M min ago" |
| vibe non-null and `display_low_min` (0.20) ≤ conf < 0.40 | `low` | vibe greyed + "low confidence" |
| conf < 0.20 or vibe null | `none` | "No fresh reports" + "Be the Scout" (bounty) CTA |

UI-only labels (frontend derives them; recs need not return them; goldens list them under `expected.ui`):
- Vibe label: 0–34 "Chill", 35–64 "Lively", 65–100 "Packed"; null → no label.
- Stale tag: `freshness_minutes > stale_tag_min` (60) → show "stale", even when display = `show`.

## 6. Trend
```
recent = eligible scout crowd reports with age ≤ trend_recent_min         (incl. future-skewed)
prior  = eligible scout crowd reports with trend_recent_min < age ≤ trend_prior_min
weights: same as §2 (H_crowd_min, decay from now)
if Σw(recent) < trend_min_weight or Σw(prior) < trend_min_weight: trend = null
Δ = wmean(recent) − wmean(prior)
Δ ≥ +trend_delta → "rising";  Δ ≤ −trend_delta → "falling";  else "steady"
```

## 7. Match score (0–100, fit to this group)
Inputs: Preferences, the **returned** (rounded) Live State, the venue row
(`venue_id, name, lat, lon` + optional `syn_venue_attributes` fields: `genres`, `capacity`, …).
Each component returns `(s_k, reason?, missing?)`; a component whose preference is null has weight 0.

| k | weight | s_k | weight 0 when | unknown (s = `unknown_component` 0.4) → `missing` |
|---|---|---|---|---|
| genre | `match_w_genre` | 1.0 a live `music_genres` slug ∈ prefs.genres; else `static_genre_score` (0.6) if venue static `genres` overlap; else 0.0 if live or static genres known; prefs.genres empty → 1.0 (no reason) | never | live `[]`/null and no static → "music unknown" |
| dancing | `match_w_dancing` | want true: dancing/2; want false: 1 − dancing/2 | want_dancing null | "no dancing reports" |
| crowd | `match_w_crowd` | 1 − \|crowd − crowd_pref\| / 4 | crowd_pref null | "no fresh reports — scores are low confidence" |
| line | `match_w_line` | max(0, 1 − 0.5·line/max_line) | max_line_minutes null | "line not reported tonight" |
| cover | `match_w_cover` | cover = 0 → 1.0; else max(0, 1 − 0.5·cover/max_cover) | max_cover_usd null | "cover not reported tonight" |
| distance | `match_w_distance` | max(0, 1 − distance_km/max_distance_km) | max_distance_km null | prefs or venue lat/lon null → "your location unknown" |
| group | `match_w_group` | min(1, capacity / (group_capacity_per_person · group_size)) | group_size null/0 | capacity null → "capacity unknown" |

```
match_score = round(100 · Σ w_k·s_k / Σ w_k)       over components with weight > 0
distance_km = haversine(prefs.lat, prefs.lon, venue.lat, venue.lon), R = earth_radius_km
missing     = the missing strings above, in table order
```

## 8. Hard-limit exclusions
Checked in this order; the first that fires is `excluded_reason`, else `excluded=false`, `excluded_reason=null`.
Only **known** values exclude; unknowns go to `missing`.

| Rule | Fires when | `excluded_reason` template |
|---|---|---|
| closed | venue `is_open_now` is `false` (backend/ml-recs evaluate OSM `opening_hours` at `now`; unparsable/unknown = `null`, never excludes) | `closed now` |
| launch | prefs `launch_only` and venue `is_launch` is `false` | `outside launch area` |
| distance | distance known and > max_distance_km | `{d:.1f} km away, over your {max:g} km` |
| cover | state cover_usd non-null and > max_cover_usd | `cover ${cover} over your ${max}` |
| line | state line_minutes non-null and > max_line_minutes | `line ~{line} min over your {max}` |

`exclude_venue_ids` (plan-night) removes venues from the output entirely.

## 9. Ranking, reasons
```
rank_score = round(match_score · (rank_conf_base + rank_conf_slope · confidence), 1)
             (returned integer match_score and 2-dp confidence; confidence null → 0)
sort key   = (excluded, −rank_score, distance_km (null last), venue_id);  rank = 1..n over all rows
```
Excluded rows come after every non-excluded row (frontend shows "N hidden by your limits").

Reasons: candidates = components with weight > 0, a reason template, and `s_k ≥ reason_min_component`;
order by `w_k·s_k` desc, ties by table order (genre, dancing, crowd, line, cover, distance, group);
keep the first `max_reasons`. Templates (normative copy; goldens check them exactly):

| k | Template |
|---|---|
| genre (live) | `{Genre} playing ({n_reports} reports, {freshness_minutes} min ago)`; operator-only: `{Genre} playing (posted by venue)` |
| genre (static) | `Usually plays {Genre}` |
| dancing | want true: `Dancing reported ({n_reports} reports)`; want false: `Low-key, little dancing` |
| crowd | `Crowd {crowd:g} of 5, close to your {crowd_pref}` |
| line | `Line ~{line} min, under your {max}` |
| cover | `No cover` if 0, else `Cover ${cover}, under your ${max}` |
| distance | `{d:.1f} km away`; under 0.1 km: `Under 0.1 km away` |
| group | `Room for your group of {group_size}` |

Genre labels: slug with first letter upper-cased, except `hip-hop` "Hip-hop", `r&b` "R&B",
`edm` "EDM", `top-40` "Top 40", `soul-funk` "Soul/funk". Slugs come from the 17-slug vocabulary
in `simulator/config/genres.json`.

Complaint risk is a separate field, `complaint_risk`, labelled "311 noise-complaint risk".
It never feeds vibe, confidence, match, rank or reasons. `cluster_label` is likewise display-only.

## 10. Run My Night (`routing.plan_night`, Later)
```
stops: greedy, n_stops (default 3); dwell = prefs.dwell_minutes or dwell_min; walk speed walk_kmh
stop j arrives at leave_at(j−1) + walk_minutes; state at arrival = predicted state if the crowd model
  is available (predicted_* keys, never overwriting observed), else the current state
candidate must pass §8 at arrival; no repeats; Σ walk minutes ≤ max_total_walk_minutes (default 30)
pick = argmax rank_score − walk_penalty_per_km · walk_km_from_prev
```
Stop shape: Contracts v2 §F. ml-recs may swap greedy for a small solver; output shape unchanged.

## 11. Golden vectors
All use `now = DEMO_NOW`, `syn-` ids, real launch `venue_id`s, `is_synthetic: 1`. Synthetic examples.

| ID | File | Case | Key expectations |
|---|---|---|---|
| G1 | `G1_normal_four_scouts.json` | 4 fresh agreeing scouts (hand-checked) | vibe **65** Packed, conf **0.67**, show, trend null |
| G2 | `G2_stale_reports.json` | G1 +120 min, plus a 200-min report | crowd null (thin), vibe null, conf 0.08, none, stale, n_reports 4 |
| G3 | `G3_single_scout.json` | 3 reports, 1 scout | diverse 0.6 → conf 0.42 |
| G4 | `G4_operator_only.json` | operator cover 20 + hip-hop | vibe null, conf 0.19, none; missing dancing/crowd/line |
| G5 | `G5_match_contract_prefs.json` | G1 + operator cover 15 + contract prefs (hand-checked) | match **83**, rank_score 76.2, `missing` [] |
| G6 | `G6_exclusion_known_vs_unknown.json` | cover $25 known vs unknown, max $20 | ATT excluded "cover $25 over your $20" and ranked after VER despite higher match; VER `missing` cover |
| G7 | `G7_disputed_and_flagged.json` | accepted, disputed, flagged, future, pending-unverified, removed | n_reports 3, vibe 46, conf 0.41 |
| G8 | `G8_trend_rising_falling.json` | 2→4, 4→2, thin prior | rising / falling / null |

Worked example G1 (synthetic example): weights 0.7573, 0.6442, 0.5355, 0.3373 (W 2.2742);
crowd 3.7646 → 3.8; dancing 1.4813 → 1.5; line median 10; vibe 65.48 → 65; support 0.7804,
sd_w 0.4243, agree 0.8586 → conf 0.67. G5 components (rounded state): genre 1.0, dancing 0.75,
crowd 0.95, line 0.667, cover 0.625, distance 0.707 (0.44 km), group 1.0 → 82.76 → **83**;
rank_score 83 · (0.75 + 0.25·0.67) = 76.2.

### File format (each vector; the bundle holds them under `vectors`)
```json
{
  "id": "G1", "name": "G1_normal_four_scouts", "description": "...", "is_synthetic": 1,
  "now": "2026-11-14T23:30:00-05:00", "hand_checked": true,
  "scouts":  [{"scout_id": "syn-s-0001", "reputation": 0.8, "is_synthetic": 1}],
  "reports": [{"report_id": "syn-r-000001", "venue_id": "0370-24-119240", "scout_id": "syn-s-0001",
               "ts": "2026-11-14T23:25:00-05:00", "crowd": 4, "dancing": 2, "line_minutes": 10,
               "cover_usd": null, "music_genre": "hip-hop", "verified_presence": 1,
               "distance_m": 40, "status": "accepted", "reputation": 0.8, "is_synthetic": 1}],
  "updates": [], "venues": [{"venue_id": "...", "name": "...", "lat": 0, "lon": 0,
               "capacity": 120, "genres": "hip-hop|house", "is_synthetic": 1}],
  "prefs": null,
  "expected": {
    "states": ["<Live Venue State per venue, sorted by venue_id>"],
    "ui": {"<venue_id>": {"vibe_label": "Packed", "stale": false}},
    "recommendations": null,
    "debug": {"<venue_id>": {"W": 2.27, "support": 0.78, "vibe_raw": 65.48, "match_raw": 82.76}}
  }
}
```
`golden_vectors.json` = `{description, is_synthetic, now, parameters, tolerance, vectors[]}`.

### How consumers test
```python
import json, pathlib
bundle = json.loads(pathlib.Path("docs/specs/golden_vectors.json").read_text())
for v in bundle["vectors"]:
    states = live_state.compute_all(v["reports"], v["updates"], v["now"])
    # compare to v["expected"]["states"] by venue_id (tolerance: bundle["tolerance"])
    if v["prefs"]:
        recs = scoring.recommend(v["prefs"], states, v["venues"], v["now"])
        # compare match_score, excluded, excluded_reason, rank, reasons, missing
```
- ml-recs: all of G1–G8; vibe ±1, confidence ±0.01, match exact, `display`/`trend`/`excluded`
  exact. Reasons/missing strings should match exactly (they are the frontend copy).
- backend: G1 (vibe 65 / conf 0.67) and G5 (match 83) through the stub and through `recs`.
- `compute_all` here returns states only for venues with inputs; the golden `states` list covers
  every venue in `venues` (G-vectors always have inputs for each).
- Change a parameter → `python -I docs/specs/tools/check_golden.py --regen`, review the diff, tell master.
