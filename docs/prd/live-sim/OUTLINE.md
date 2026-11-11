# OUTLINE: live-sim build plan

Sizes: **S** < 1 h, **M** 1–3 h, **L** 3–6 h. Updated for CONTRACTS v2.
Deadline: pushed by **Fri 2026-11-13 18:00 ET** (v2 §I); integration merges live-sim
after coursework, deploy dry-run Nov 15, freeze Nov 16 20:00, demo Nov 17.

## 1. Ordered tasks

### Phase A: skeleton (Thu Nov 12, morning)
- [ ] A1 **S** `simulator/` package; `__main__.py` with subcommands `extract-inputs`,
      `generate`, `validate`, `load`, `build` (= generate + validate + load), `replay`.
- [ ] A2 **S** `genres.py`: `GENRES` = the 20 values of CONTRACTS v2 §E, `is_genre()`.
      Push this first so research can use it.
- [ ] A3 **S** `config.py` + `config/default.json`, `small.json` (2 weeks, 20 scouts,
      for tests), `demo.json`; config hash; `DEMO_NOW`, `LIVE_SIM_DB` from env with defaults.
- [ ] A4 **S** `rng.py`: master seed → per-stage `Generator` via SeedSequence keyed by
      sha256(stage name).
- [ ] A5 **M** `schema.py`: column lists, dtypes, enums, nullability for all 12 tables
      from CONTRACTS v2 §E; `check(df, table)`.
- [ ] A6 **S** `timeutil.py`: 33 nights (Thu–Sat, 2026-09-03 → 2026-11-14), 20:00–03:00
      ET, 15-min UTC grid, `to_local_iso()`, DST-safe.
- [ ] A7 **S** `extract.py` + `simulator extract-inputs` → `simulator/data/venue_inputs.csv`
      (35 rows, real public data incl. OSM `opening_hours`). Commit it.

### Phase B: world (Thu Nov 12)
- [ ] B1 **M** `venues.py`: style rules → priors; dance floor, capacity, cover, genres
      (from `GENRES`), price level, `is_claimed`, `opening_hours`; hidden popularity;
      apply `data/venue_attributes_manual.csv` if present. → `syn_venue_attributes`.
- [ ] B2 **S** `updates.py` (plan step): which claimed venues post what each night,
      events that boost true crowd. → `syn_venue_updates` rows written later.
- [ ] B3 **L** `truth.py`: style curves, weekday, shocks, AR(1), opening hours, event
      boosts, mapping to contract scales. → `syn_true_state`.

### Phase C: people and nightly loop (Thu Nov 12 – Fri Nov 13 morning)
- [ ] C1 **L** `scouts.py`: weekly cohorts, archetypes, home venues for shills, latent
      engagement with weekly decay/bumps, churn date, returns. → `syn_scout_truth`.
- [ ] C2 **L** `nightloop.py`: per night, per 15-min slot: scouts choose venues
      (distance, taste, open bounties), observations from truth with archetype
      noise/bias, `distance_m`/`verified_presence`, rate-limit drops, null rates;
      every 15 min from 21:00 to 02:00 compute confidence/freshness and create/expire/
      claim bounties (specs §7.5). → raw reports + `syn_bounties`.
- [ ] C3 **S** `_confidence.py`: minimal specs §5.2/5.3/5.6 copy (or `recs.live_state`
      if importable); unit test against golden vector G1.
- [ ] C4 **M** `trust.py`: time-ordered post-pass: velocity and outlier flags, disputes
      (→ `syn_disputes`, `disputed`/`removed`), reputation per specs §7.1, points per
      §7.2 (→ `syn_points_ledger`), levels; weekly engagement feedback to C1.
      → final `syn_scout_reports`, `syn_scouts` (incl. `last_active_at`).
- [ ] C5 **M** `users.py`: home mixture, persona prefs → `prefs_json`. → `syn_users`.
- [ ] C6 **M** `events.py`: user sessions → impressions/taps/saves/views by venue busyness.
      → `syn_venue_events` (fallback: Poisson by hour × busyness).
- [ ] C7 **M** `feedback.py`: placeholder chooser over true state. → `syn_feedback`.

### Phase D: outputs and tooling (Fri Nov 13)
- [ ] D1 **S** `io.py`: deterministic CSV writer, `syn-` ID assignment, `manifest.json`.
- [ ] D2 **M** `validate.py`: schema, integrity, specs-rule and realism checks (§5) →
      `validation.json`, non-zero exit on failure.
- [ ] D3 **S** `load.py`: write tables into `data/live_sim.db` (or `LIVE_SIM_DB`);
      refuses any name not `^syn_[a-z_]+$` and refuses a target named `manhattan_bars.db`;
      indexes; row-count check.
- [ ] D4 **M** `replay.py`: `visible(tables, now)` (incl. derived `pending`), `snapshot(now)`,
      `shift(tables, to_date)`; CLI printing.
- [ ] D5 **S** `extracts.py`: hourly by style × weekday; Sat Nov 14 20:00–03:00 15-min
      per-venue snapshots (lat, lon, true crowd, n_reports_60m, open bounty).

### Phase E: tune, document, push (Fri Nov 13, by 18:00 ET)
- [ ] E1 **M** Tune config until `validate` passes on seed 42.
- [ ] E2 **S** `docs/synthetic/live-sim.md` registry (all 12 tables).
- [ ] E3 **S** `docs/workstreams/live-sim.md`: how to run, limits, open issues, CCRs.
- [ ] E4 **S** `.gitignore` entries for `data/live_sim.db`, `data/synthetic_live/*.csv`,
      `data/synthetic_live/shifted/`; commit manifest/validation; push; tell master.

### Later (after Nov 17)
- [ ] L1 **M** `stream.py`: post reports to `POST /api/reports` at N× speed.
- [ ] L2 **M** `feedback.py` uses `recs.scoring.recommend` (`--recommender`).
- [ ] L3 **L** More venues; special-night configs; calibration to pilot data.

Total MVP estimate: ~30–38 h of build work; phases C2 and C4 are the critical path.

## 2. File tree to be created

```
simulator/
  __init__.py            # generate(cfg) -> dict[str, DataFrame]; __version__
  __main__.py            # CLI
  genres.py              # GENRES (shared vocabulary, CONTRACTS v2 §E)
  config.py
  rng.py
  schema.py
  timeutil.py
  extract.py
  venues.py
  updates.py
  truth.py
  scouts.py
  nightloop.py
  _confidence.py         # SYNTHETIC mirror of specs §5.6 (bounty trigger only)
  trust.py
  users.py
  events.py
  feedback.py
  io.py
  validate.py
  load.py
  replay.py
  extracts.py
  data/venue_inputs.csv  # real public inputs for the 35 venues (is_synthetic=0)
  config/default.json
  config/small.json
  config/demo.json
  tests/
    conftest.py
    test_genres.py
    test_schema.py
    test_determinism.py
    test_timeutil.py
    test_truth.py
    test_scouts.py
    test_nightloop.py
    test_trust.py
    test_confidence.py
    test_load.py
    test_replay.py
    test_validate.py
  requirements-dev.txt
data/synthetic_live/      # CSVs gitignored; manifest + validation committed
  syn_venue_attributes.csv  syn_scouts.csv  syn_users.csv  syn_scout_reports.csv
  syn_venue_updates.csv  syn_feedback.csv  syn_bounties.csv  syn_venue_events.csv
  syn_disputes.csv  syn_points_ledger.csv
  syn_true_state.csv  syn_scout_truth.csv        # evaluation only
  manifest.json  validation.json
  extracts/hourly_by_style.csv  extracts/tonight_2026-11-14.csv
  shifted/                                       # replay --shift-to output
data/live_sim.db          # built, never committed
docs/synthetic/live-sim.md
docs/workstreams/live-sim.md
```

## 3. Interfaces

### Consumed
| From | What | Ref |
|---|---|---|
| existing | `data/launch_venues.csv`, `venue_features`, `osm_venues` (read once by `extract-inputs`) | CONTRACTS "Launch venues", v2 §D |
| team | `data/venue_attributes_manual.csv` (optional, read-only) | v2 §D |
| contracts | table schemas, Preferences JSON, synthetic rule, IDs, `DEMO_NOW`, `LIVE_SIM_DB` | base + v2 §B, D, E, H |
| specs | §5.2/5.3/5.6 freshness, weights, confidence; §7.1 reputation; §7.2 points/levels; §7.3 anti-gaming; §7.4 status/disputes; §7.5 bounties; churn label 14 days; golden vector G1 | `docs/prd/specs/PRD.md` |
| ml-recs (optional) | `recs.live_state.compute(...)` for bounty confidence | CONTRACTS "Python interface" |

### Provided
| To | What |
|---|---|
| backend | `python -I -m simulator build` → `data/live_sim.db` (all `syn_` tables, v2 §E); `simulator.replay.visible(tables, now)` defines `now=` visibility and derived `pending` status |
| ml-recs | all tables + `syn_true_state`, `syn_scout_truth`; holdout = nights of 2026-11-13 and 2026-11-14, train = 31 nights before; `simulator.generate(cfg)` for in-memory runs |
| coursework | `syn_scouts`, `syn_scout_reports`, `syn_points_ledger`, `syn_bounties` over 11 weeks; `syn_scout_truth.latent_churn_date` |
| tableau | `data/synthetic_live/extracts/*.csv` (tableau copies into `analytics/tableau/extracts/synthetic/`) |
| research | `from simulator.genres import GENRES` |
| frontend | demo content via backend; list of synthetic fields for badges (registry) |
| integration | `simulator build` (seed 42, deterministic); `DEMO_NOW = 2026-11-14T23:30:00-05:00`; `--shift-to 2026-11-17` |

CLI:
```
python -I -m simulator extract-inputs                      # once; needs data/manhattan_bars.db
python -I -m simulator build [--seed 42] [--preset default|small|demo] [--db data/live_sim.db]
python -I -m simulator generate | validate | load          # the three steps of build
python -I -m simulator replay --now 2026-11-14T23:30:00-05:00 [--venue <id>] [--shift-to 2026-11-17]
```

Python:
```python
import simulator
from simulator.genres import GENRES
tables = simulator.generate(simulator.config.load("default", seed=42))   # dict[str, DataFrame]
from simulator import replay
seen = replay.visible(tables, now="2026-11-14T23:30:00-05:00")
```

## 4. Synthetic datasets

Swap path for every app table (v2 §E): real rows go into the same-named table
without `syn_` (e.g. `scout_reports`); backend reads `UNION ALL`;
`INCLUDE_SYNTHETIC=0` hides synthetic rows; then stop running `simulator build`.

| Table | Imitates | How generated | Real source |
|---|---|---|---|
| `syn_venue_attributes` | style, genres, dance floor, cover, capacity, price, claimed, hours | `venues.py` rules + priors; OSM hours are real | `data/venue_attributes_manual.csv` now; claimed operator profiles later |
| `syn_scouts` | Scout accounts and stats | `scouts.py` + `trust.py` | backend scouts table (demo-login, then real auth) |
| `syn_users` | users and saved prefs | `users.py` personas | onboarding answers |
| `syn_scout_reports` | 10-second vibe checks with status and distance | `nightloop.py` + `trust.py` | `POST /api/reports` |
| `syn_venue_updates` | operator posts and offers | `updates.py` | `POST /api/owner/{id}/updates` |
| `syn_feedback` | post-visit outcomes | `feedback.py` placeholder chooser | `POST /api/feedback` |
| `syn_bounties` | bounty board | `nightloop.py` per specs §7.5 | backend bounty job on real confidence |
| `syn_venue_events` | views, taps, saves, impressions | `events.py` funnel | frontend/backend event logging |
| `syn_disputes` | owner/user disputes | `trust.py` | dispute endpoint + moderator script |
| `syn_points_ledger` | points awarded/clawed back | `trust.py` per specs §7.2 | backend points service |
| `syn_true_state` | the unobservable real state (eval only) | `truth.py` | none; proxies later (door counts, verified check-ins) — drop when real |
| `syn_scout_truth` | honest vs gaming; latent churn (eval only) | `scouts.py` | moderation outcomes, real last-active — drop when real |
| extracts | tableau inputs | `extracts.py` | same queries on real tables |

Key placeholder numbers (all in `default.json`, each `# SYNTHETIC:`): style peaks,
weekday 0.70/0.95/1.00, shocks σ 0.15/0.20, Halloween ×1.3, crowd bins
0.2/0.45/0.7/0.9, line above 85% occupancy, ~150 scouts (50 + 5–15/week),
engagement decay 0.85 and churn threshold 0.25, archetype shares
55/25/10/6/4, null rates 60%/40%, 300 users, funnel 25%/10%, dispute rate 3% and
uphold 30%, events cap ~150k rows. Expected volume: ~300–700 reports/night,
~15k reports total.

## 5. Test plan

| Test | What it checks | Data |
|---|---|---|
| `test_genres` | `GENRES` equals CONTRACTS v2 list (20 values, lowercase, unique) | unit |
| `test_schema` | exact columns/order per v2 §E, dtypes, enums (status, event_type, archetype), ranges, nulls, `is_synthetic=1`, `syn-` IDs, prefs_json | small preset |
| `test_determinism` | same seed → same sha256 per CSV; different seed differs; stage isolation (users config change leaves reports unchanged) | small ×2 |
| `test_timeutil` | 33 nights, Thu–Sat only, 20:00–03:00; Oct 31 night across DST: UTC monotonic, offsets −04:00 → −05:00 | unit |
| `test_truth` | peaks per style; Sat ≥ Fri ≥ Thu; closed ⇒ occupancy 0 | small |
| `test_scouts` | weekly cohorts; no reports after `latent_churn_date` (except returns); churn share in range on default config | small + default (marked slow) |
| `test_nightloop` | rate limits never exceeded; `verified_presence` ⇔ distance ≤ 150; bounties ≤ 8 open, expire at 60 min, claim = first accepted verified report | small |
| `test_trust` | velocity and outlier flags on hand-made cases; reputation update matches specs §7.1 examples; ledger sums to points; levels thresholds | unit + small |
| `test_confidence` | golden vector G1 → conf 0.67 | unit |
| `test_load` | only `syn_*` tables; refuses bad names and `manhattan_bars.db` target; row counts match | temp DB |
| `test_replay` | nothing after `now + 2 min`; `pending` iff < 30 min and not flagged; expired offers/bounties hidden; shift keeps time of night | small |
| `test_validate` | validator passes on small preset; a broken table fails | small |

`validate.py` on the full output also checks: report peaks 22:00–01:00; club/dive vs
cocktail ordering at 01:00 and 20:30; honest MAE ≤ 0.6, gamer/shill ≥ 1.2; ≥ 20% empty
venue-slots; churn 40–60% and week-4 retention 35–60%; 14-day label vs latent churn
agreement ≥ 80%; feedback Spearman ≥ 0.3; at `DEMO_NOW` ≥ 25 venues fresh and ≥ 3 open
bounties; all genres in `GENRES`; CSV total ≤ 30 MB.

## 6. Demo script (Nov 17, ~2 min of the integration demo)

1. `python -I -m simulator build` → manifest row counts; "seed 42, every row `is_synthetic = 1`".
2. Show `validation.json` green: nightly peaks, weekday order, honest vs gamer error,
   Scout drop-off curve.
3. `replay --now 2026-11-14T21:00:00-05:00` → cocktail bars filling, offers live, few reports.
4. `replay --now 2026-11-14T23:30:00-05:00` (DEMO_NOW) → 25+ venues fresh, bounties
   open at busy but unreported venues, a few reports still `pending`.
5. `replay --now 2026-11-15T01:30:00-05:00` → late peak at dives/clubs; a shill's
   flagged outlier next to honest reports (ml-recs shows it weighted to 0).
6. In the deployed app at `?now=2026-11-14T23:30:00-05:00`: same story with the
   "demo data" badge; owner dashboard demand curve comes from `syn_venue_events`.
7. Close on `docs/synthetic/live-sim.md` and `INCLUDE_SYNTHETIC=0`: "this is how every
   fake row gets switched off once real Scouts report."
