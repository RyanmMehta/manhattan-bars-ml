# OUTLINE: live-sim build plan

Sizes: **S** < 1 h, **M** 1–3 h, **L** 3–6 h. Target: MVP done and seed frozen by
Sun 2026-11-15, two days before Nov 17 integration.

## 1. Ordered tasks

### Phase A: skeleton (Nov 12)
- [ ] A1 **S** Create `simulator/` package, `__main__.py` with argparse subcommands
      (`generate`, `validate`, `load`, `replay`), `requirements-dev.txt`.
- [ ] A2 **S** `config.py`: load `config/default.json`, merge `--config` overrides,
      compute config hash; `presets` for `default`, `small` (2 nights, 10 scouts,
      for tests) and `demo`.
- [ ] A3 **S** `rng.py`: master seed → per-stage `Generator` via SeedSequence keyed
      by sha256(stage name).
- [ ] A4 **S** `schema.py`: column lists, dtypes, enums, nullability for the 7
      contract tables + 3 evaluation tables (truth, scout truth, reputation history), copied from CONTRACTS.md; `check(df, table)`.
- [ ] A5 **S** `timeutil.py`: night windows (Thu–Sat, 18:00–04:00 local) → UTC
      15-min grid; `to_local_iso()`; DST-safe.

### Phase B: world (Nov 12–13)
- [ ] B1 **M** `venues.py`: read launch venues + `venue_features`, apply style
      rules → overrides CSV → priors; draw dance floor, capacity, cover, genres
      (from `config/genres.json` only),
      price level, `is_claimed`; hidden `popularity`. Output `syn_venue_attributes`.
- [ ] B2 **S** `config/venue_style_overrides.csv` with a column `source`
      (`rule` / `team_guess`) and blank rows for the 35 venues to fill in.
- [ ] B3 **L** `truth.py`: true-state engine. Style hourly curves, weekday factor,
      night shock, venue-night shock, AR(1) step noise, event boosts (from updates
      plan), mapping to crowd/dancing/line/cover/genre. Output `syn_true_state`.

### Phase C: people and events (Nov 13–14)
- [ ] C1 **M** `scouts.py`: scouts with archetypes, home venue for shills, join
      dates by weekly cohort, activity propensity, weekly churn hazard
      (archetype × engagement), optional return. Output `syn_scout_truth`
      (+ draft `syn_scouts`). Size now **L** because of the lifecycle.
- [ ] C2 **L** `reports.py`: per night, scout itineraries (venue choice by
      distance + taste, stay length), report times, observation model per
      archetype, gamer bursts/copies, null rates, `verified_presence`. Output
      `syn_scout_reports`.
- [ ] C3 **M** `updates.py`: operator posts and offers for claimed venues; 10%
      stale/wrong; events feed back into `truth.py` as boosts (generate the
      update *plan* before truth, write rows after). Output `syn_venue_updates`.
- [ ] C4 **M** `bounties.py`: every 30 min 21:00–02:00, bounty if expected crowd
      ≥ 3 and no report in 60 min; claim when a scout reports within 30 min (C2
      gets a second pass that sends nearby scouts to bounty venues). Output
      `syn_bounties`.
- [ ] C5 **M** `scouts.finalize()`: points, level, reports_count, reputation
      (placeholder rules) recomputed night by night → `syn_scout_reputation_history`;
      last snapshot → final `syn_scouts`. Engagement from each night feeds the next
      week's churn hazard, so C1/C2/C5 run in a weekly loop.
- [ ] C6 **M** `users.py`: users with home lat/lon mixture and persona prefs →
      `prefs_json`. Output `syn_users`.
- [ ] C7 **M** `feedback.py`: placeholder chooser over true state, visited and
      rating. Output `syn_feedback`.

### Phase D: outputs and tooling (Nov 14)
- [ ] D1 **S** `io.py`: deterministic CSV writer, `manifest.json` (seed, config
      hash, git commit, version, row counts, sha256 per file).
- [ ] D2 **M** `validate.py`: schema, integrity and realism checks (section 6) →
      `validation.json`, non-zero exit on failure.
- [ ] D3 **S** `load.py`: write `syn_*` tables into SQLite (replace), name guard,
      indexes on `(venue_id, ts)`, row-count check.
- [ ] D4 **M** `replay.py`: `visible(tables, now)`, `snapshot(now)` per-venue
      summary, `shift(tables, from_date, to_date)`; CLI printing.
- [ ] D5 **S** `extracts.py`: hourly crowd and report volume by style × weekday CSV
      for tableau (`data/synthetic_live/extracts/`).

### Phase E: docs, tuning, freeze (Nov 15)
- [ ] E1 **M** Tune config until all realism checks pass with seed 42; spot-check
      plots in a scratch notebook (not committed).
- [ ] E2 **S** `docs/synthetic/live-sim.md` registry.
- [ ] E3 **S** `docs/workstreams/live-sim.md`: how to run, limits, open issues,
      contract change requests.
- [ ] E4 **S** Generate with pinned seed, commit CSVs, push, notify master session.

### Later (after Nov 17)
- [ ] L1 **M** `stream.py`: post reports to `POST /api/reports` at N× speed.
- [ ] L2 **M** Plug `recs.scoring.recommend` into `feedback.py` (`--recommender`).
- [ ] L3 **M** `syn_venue_demand` (views, taps, saves) if accepted.
- [ ] L4 **L** Extend to all 10002 venues / `v_bars`; special-night configs.

Total MVP estimate: ~30–40 h (scout lifecycle and 12-week loop added).

## 2. File tree to be created

```
simulator/
  __init__.py            # generate(cfg) -> dict[str, DataFrame]; __version__
  __main__.py            # CLI
  config.py
  rng.py
  schema.py
  timeutil.py
  venues.py
  truth.py
  scouts.py
  reports.py
  updates.py
  bounties.py
  users.py
  feedback.py
  io.py
  validate.py
  load.py
  replay.py
  extracts.py
  config/
    default.json
    small.json
    demo.json            # Fri 2026-11-13, 20:00–03:00 view, seed 42
    genres.json          # shared genre vocabulary (version 1)
    venue_style_overrides.csv
  tests/
    conftest.py          # tiny config, temp dirs, temp DB copy
    test_schema.py
    test_determinism.py
    test_timeutil.py
    test_truth.py
    test_reports.py
    test_load.py
    test_replay.py
    test_validate.py
  requirements-dev.txt
data/synthetic_live/
  syn_venue_attributes.csv
  syn_scouts.csv
  syn_users.csv
  syn_scout_reports.csv
  syn_venue_updates.csv
  syn_feedback.csv
  syn_bounties.csv
  syn_true_state.csv      # evaluation only
  syn_scout_truth.csv     # evaluation only
  syn_scout_reputation_history.csv
  manifest.json
  validation.json
  extracts/hourly_by_style.csv
  demo_shifted/           # output of replay --shift-to (gitignored or regenerated)
docs/synthetic/live-sim.md
docs/workstreams/live-sim.md
```

## 3. Interfaces

### Consumed
| From | What | Ref |
|---|---|---|
| existing | `data/launch_venues.csv`; `venues`, `venue_features` tables (read-only) | CONTRACTS.md "Launch venues" |
| contracts | 7 `syn_` table schemas, Preferences JSON, synthetic-data rule | CONTRACTS.md "Data schemas", "Preferences" |
| specs | style enum, points/reputation/level formulas, half-life | `docs/specs/` (placeholders until published) |
| research | persona shares, cover/line ranges | `research/` (placeholders until published) |
| ml-recs (later) | `recs.scoring.recommend(prefs, states, venues, now)` | CONTRACTS.md "Python interface" |

### Provided
| To | What |
|---|---|
| backend | CSVs in `data/synthetic_live/`; `python -I -m simulator load --db <path>`; `simulator.replay.visible(tables, now)` defining `?now=` |
| ml-recs | contract tables + `syn_true_state`, `syn_scout_truth`; `simulator.generate(cfg)` for in-memory runs; `syn_scout_reputation_history` for as-of reputation joins; temporal split: test = last 2 nights (2026-11-13, 2026-11-14), train = the 34 nights before |
| tableau | `data/synthetic_live/extracts/*.csv` |
| frontend | demo night content via backend; list of synthetic fields for badges (registry) |
| tableau | `extracts/` plus `extracts/demo_night_snapshots.csv` (every 30 min, Fri 2026-11-13 20:00–03:00, per venue: lat, lon, true crowd, n_reports_60m) for the tonight heatmap |
| coursework | `syn_scouts`, `syn_scout_reports`, `syn_scout_reputation_history` over 12 weeks; `syn_scout_truth.churned_at` for sanity checks |
| research | `simulator/config/genres.json` (shared genre vocabulary) |
| integration | pinned seed (42), `--preset demo`, demo night Fri 2026-11-13 (20:00–03:00), live at 23:30, shifted to 2026-11-17 |

CLI:
```
python -I -m simulator generate [--seed 42] [--preset default|small|demo] [--config x.json] [--out data/synthetic_live]
python -I -m simulator validate [--out data/synthetic_live]
python -I -m simulator load --db data/manhattan_bars.db [--out data/synthetic_live]
python -I -m simulator replay --now 2026-11-13T23:30 [--venue <id>] [--shift-to 2026-11-17]
```

Python:
```python
import simulator
tables = simulator.generate(simulator.config.load("default", seed=42))   # dict[str, DataFrame]
from simulator import replay
seen = replay.visible(tables, now="2026-11-13T23:30:00-05:00")          # same keys, filtered
```

## 4. Synthetic datasets

| Table | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `syn_venue_attributes` | static facts: style, genres, dance floor, cover, capacity, price | `venues.py` rules on OSM/DOHMH/name + overrides + priors | claimed operator profiles; team field survey; Google/Yelp attributes if terms allow | create `venue_attributes` with same columns, `is_synthetic=0`; point backend at it; drop syn table |
| `syn_scouts` | Scout accounts and stats | `scouts.py` archetypes + `finalize()` | real `scouts` table from backend auth + scoring | backend writes real table; stop loading syn |
| `syn_users` | app users and saved prefs | `users.py` persona mixture | real user accounts / onboarding answers | same |
| `syn_scout_reports` | 10-second vibe checks | `reports.py` itineraries + noisy observations of truth | `POST /api/reports` rows from pilot | backend stores real `scout_reports`; live_state reads it; syn kept only for tests |
| `syn_venue_updates` | operator posts, offers | `updates.py` | owner dashboard `POST /api/owner/{id}/updates` | same |
| `syn_feedback` | post-visit outcomes | `feedback.py` placeholder chooser + fit-based rating | in-app "did you go / rate it" prompt | same |
| `syn_bounties` | bounty board | `bounties.py` gap rule | backend bounty service using real report gaps | same |
| `syn_true_state` | the unobservable real state of each venue | `truth.py` curves + shocks | none (no real ground truth exists); proxy: door counts or verified check-ins in pilot | evaluation only; drop when real data used |
| `syn_scout_truth` | who is honest vs gaming; true accuracy; true churn week | `scouts.py` archetypes + lifecycle | moderation outcomes / dispute decisions; real last-active dates | evaluation only |
| `syn_scout_reputation_history` | reputation/points as they stood each night | `scouts.finalize()` nightly recompute | backend reputation snapshots (nightly job) | backend writes real history table; ml-recs as-of join unchanged |
| `extracts/hourly_by_style.csv` | aggregated activity for Tableau | `extracts.py` | same query over real reports | rerun extract on real tables |

Placeholder realism numbers (all in `default.json`, all `# SYNTHETIC:`):
- Style peak hours: dive 23–01, cocktail 21–23, club 00–02, lounge 22–00,
  pub 20–23, restaurant-bar 19–21.
- Weekday factor: Thu 0.70, Fri 0.95, Sat 1.00. Night shock lognormal σ 0.15;
  venue-night σ 0.20. Labor Day weekend (Sat Sep 5) ×1.15, Halloween (Sat Oct 31) ×1.3.
- Window: 12 weeks, Thu 2026-08-27 → Sat 2026-11-14 (36 nights).
- Crowd bins on occupancy fraction: <0.2→1, <0.45→2, <0.7→3, <0.9→4, else 5.
- Line minutes ≈ 0 below 85% occupancy, then ~ 40 × (occ − 0.85)/0.15 + noise, cap 45.
- Scouts ≈ 150 ever joined (50 at launch, 5–15/week), 40–60 active per week;
  weekly churn hazard ≈ 0.12 base, ×0.6 with a bounty win, ×1.8 after an idle week;
  reports/night ≈ 300–700 total (≈ 18k rows over 36 nights); users 300.
- Null rates: cover 60%, music_genre 40%.

## 5. Test plan

| Test | What it checks | Data |
|---|---|---|
| `test_schema` | exact columns/order, dtypes, enums, ranges, nullability, `is_synthetic=1`, `syn-` IDs, prefs_json shape | small preset |
| `test_determinism` | same seed → identical sha256 per file; different seed → different; stage isolation | small preset ×2 |
| `test_timeutil` | night windows, 15-min grid, Oct 31→Nov 1 DST night: UTC monotonic, local offsets −04:00 then −05:00 | unit |
| `test_truth` | curve peaks per style at configured hours; Sat ≥ Fri ≥ Thu means | small preset, 3 nights |
| `test_scouts` | cohorts join weekly; churned scouts file no reports after `churned_at`; reputation history is as-of (no row uses reports from later nights) | small preset with 4 weeks |
| `test_reports` | honest MAE vs truth < gamer MAE; gamer bursts exist; null rates within ±10 pts of target; reports only inside night windows | small preset |
| `test_load` | only `syn_*` created/replaced; non-syn tables unchanged (checksum on temp DB copy); bad name raises; row counts match | temp DB |
| `test_replay` | no `ts > now`; expired offers and claimed/expired bounties hidden; shift keeps time-of-night and weekday labels | small preset |
| `test_validate` | full validator passes on small preset; a deliberately broken table fails | small preset |

Validation checks in `validate.py` (run on full output): all schema checks; peak
report volume 22:00–01:00 each night; Sat ≥ Fri ≥ Thu at 23:00; club > cocktail
at 01:00 and reverse at 20:00; honest MAE ≤ 0.6, gamer/shill ≥ 1.2; ≥ 20%
empty venue-slots 21:00–02:00; 12-week churn 40–60% and week-4 cohort retention 35–60%; all genres in `genres.json`; feedback rating vs true fit Spearman ≥ 0.3; output
≤ 20 MB.

## 6. Demo script (Nov 17, ~2 min of the integration demo)

1. `python -I -m simulator generate --seed 42` → show manifest row counts and
   "is_synthetic = 1 on every row".
2. `python -I -m simulator validate` → green checklist (peaks, weekday order,
   honest vs gamer error).
3. `python -I -m simulator replay --now 2026-11-13T21:00` → mostly quiet, cocktail
   bars filling, offers live.
4. `--now 2026-11-13T23:30` → clubs climbing, 25+ venues with fresh reports, open
   bounties at unreported busy venues.
5. `--now 2026-11-14T01:30` → club peak, a shill scout's inflated report visible
   next to honest ones (ml-recs then shows reputation weighting discount it).
6. In the deployed app: same `now=` param on `/api/venues` and `/api/heatmap`
   shows the same story with the "demo data" badge.
7. Close: point at `docs/synthetic/live-sim.md` — "every row here is fake, and here
   is exactly how it gets replaced by real Scout data".
