# PRD: live-sim (time-based synthetic nightlife simulator)

Workstream: `live-sim` · Branch: `nightlife/live-sim` · Owns: `simulator/`, `data/synthetic_live/`, writes `data/live_sim.db`
Status: planning (no code yet) · Updated: 2026-11-11 for **CONTRACTS v2.2** (commit b46d75f)
Rules it implements: `docs/CONTRACTS.md` (v2 amendments override the base text) and
specs' scoring/trust rules in `docs/prd/specs/PRD.md` §5–7 on `nightlife/specs`.

Numbers marked *(placeholder)* are reasoned guesses to be tuned during the build,
not measured facts. Constants owned by specs are quoted with their section and are
not redefined here.

## 1. Problem

Nightlife Autopilot ranks venues by what is happening *right now*: crowd, dancing,
line, cover, music. None of that exists in the public pipeline. The database has
5,737 licensed venues with licenses, inspections, 311 complaints and OSM tags, but
no scouts, no reports, no users, no operator posts, no app usage and no outcomes.
Without live-like data:

- `ml-recs` has nothing to compute Live Venue State from and no nights to train or
  hold out for the crowd model.
- `backend` has empty tables behind every live endpoint and the owner dashboard.
- `coursework` has no Scout activity history for the churn exercise.
- `tableau` has no hourly patterns or "tonight" heatmap.
- The Nov 17 demo (replaying `DEMO_NOW = 2026-11-14T23:30:00-05:00`) has nothing to replay.

We need one deterministic source of fake-but-plausible nightlife activity for the
35 LES launch venues. It has to cover 12 weeks of Thu–Sat nights, include messy and
dishonest Scouts who drop off over time, keep a hidden ground truth for evaluation,
and be easy to switch off once real data arrives (`INCLUDE_SYNTHETIC=0`).

## 2. Goals

1. Generate every live-sim table in CONTRACTS v2.1 §E, column for column:
   `syn_venue_attributes`, `syn_scouts`, `syn_users`, `syn_scout_reports`,
   `syn_venue_updates`, `syn_feedback`, `syn_bounties`, `syn_venue_events`,
   `syn_disputes`, `syn_points_ledger`, `syn_scout_reputation_history`, plus the
   evaluation-only `syn_true_state` and `syn_scout_truth` (13 tables), and the
   demo-night snapshot CSV for tableau (v2.2 §J).
2. Make it time-based: **Thu–Sat nights, Thu 2026-08-27 → Sat 2026-11-14, 36 nights,
   20:00–03:00 ET** (v2 §B). Reports follow hourly arrival curves by venue style,
   weekday, opening hours and night-level shocks.
3. Model Scouts realistically: archetypes (honest, casual, sloppy, gamer, shill), a
   latent engagement process with drop-off (v2 §B), rate limits and anti-gaming
   outcomes per specs §7.
4. Apply specs' rules for report `status`, points, levels, reputation and bounties,
   so backend, ml-recs and the simulator agree on what each row means.
5. Keep hidden ground truth (true venue state every 15 min, true scout archetype and
   latent churn date) for evaluation only.
6. Be deterministic: seed 42 and the same config give byte-identical CSVs and the
   same `data/live_sim.db` contents.
7. Ship the fixed build command `python -I -m simulator --seed 42 --out data/live_sim.db` (v2.2 §J; `--nights N` quick mode), plus
   `validate` and `replay` helpers for any `now=`.
8. Own the shared genre vocabulary at `simulator/config/genres.json` (17 slugs, v2.1 §E),
   with `simulator/genres.py` as a thin loader exposing `GENRES` to Python users.
9. Follow the synthetic-data rule completely (`is_synthetic=1`, `syn_` tables, `syn-`
   IDs, `# SYNTHETIC:` comments, registry in `docs/synthetic/live-sim.md`).

## 3. Non-goals

- Not a recommender or Live Venue State service. `ml-recs` owns `recs/`. The simulator
  carries a minimal fallback of specs §5 (vibe, confidence, freshness) only to decide
  when bounties appear and to fill the demo-night snapshots, and uses
  `recs.live_state` whenever it is importable.
- No HTTP API. `backend` serves the data and attaches `data/live_sim.db`.
- No claims about real venues. Attributes for real, named LES bars are guesses and
  must never be shown without the "demo data" badge.
- Not fitted to real Scout data (none exists). Realism comes from stated rules (§7).
- No writes to `data/manhattan_bars.db`, `src/`, `CONTRACTS.md`, or other workstreams'
  folders. `data/venue_attributes_manual.csv` is read, never written.
- MVP covers the 35 launch venues only (the generator takes a venue list).

## 4. Users of this workstream

| User | What they need from live-sim |
|---|---|
| ml-recs | 36 nights of reports and updates; `syn_true_state` to score `live_state`; temporal holdout = last 2 nights (Fri Nov 13, Sat Nov 14); `syn_scout_reputation_history` for as-of reputation joins |
| backend | `data/live_sim.db` built deterministically; `syn_` tables matching v2 §E; replay rules for `now=` (status as of `now`, open bounties, live offers) |
| coursework | ≥ 10 weeks of Scout activity with realistic drop-off; `syn_scout_truth.churned_at` for sanity checks |
| tableau | `data/synthetic_live/demo_night_snapshots.csv` (Sat Nov 14, every 30 min 20:00–03:00) and hourly extracts |
| frontend | believable demo content at `DEMO_NOW`: cards, leaderboard, bounties, offers, owner dashboard |
| research | `simulator/config/genres.json` so `syn_interviews` / `syn_survey_responses` share one genre list |
| integration | one command that builds `data/live_sim.db` from seed 42 on any machine, without the 39 MB public DB |

## 5. User stories and acceptance criteria

**LS-1 Generate the season.**
- `python -I -m simulator --seed 42 --out data/live_sim.db` writes all 13 tables as CSV to
  `data/synthetic_live/` and loads them into `data/live_sim.db` in < 60 s for the full
  36-night run on a laptop CPU (v2.2 §J). It runs at build time (Render build command,
  integration's `make data`), not at app boot.
- `--nights N` quick mode generates only the last N nights ending Sat Nov 14 (so the
  demo night is always included); tests use `--nights 3`.
- 36 nights, Thu 2026-08-27 → Sat 2026-11-14, events only between 20:00 and 03:00 ET
  (the Sat Oct 31 night crosses the DST fall-back on Nov 1 and must have valid,
  ordered timestamps).
- Every row has `is_synthetic = 1`; every column matches CONTRACTS v2.
- It runs without `data/manhattan_bars.db`: real venue inputs come from a committed
  35-row extract (`simulator/data/venue_inputs.csv`, real public data, no synthetic values).

**LS-2 Realistic nightly rhythm.**
- Report volume across venues peaks between 22:00 and 01:00 on every night.
- Mean true crowd at 23:00: Sat ≥ Fri ≥ Thu.
- At 01:00, `club` and `dive` venues have higher mean true crowd than `cocktail` and
  `restaurant-bar`; at 20:30 the order flips.
- No reports or true crowd > 1 while a venue is closed per its OSM `opening_hours`
  (when known).

**LS-3 Messy and dishonest Scouts.**
- Archetypes in `syn_scout_truth`: honest 55%, casual 25%, sloppy 10%, gamer 6%,
  shill 4% *(placeholders; gamer + shill = specs' 10% "gaming scouts")*.
- Gamers: always crowd 5 or random venues, bursts, low `verified_presence`, large or
  null `distance_m`. Shills: inflate one home venue (+2 crowd).
- Rate-limit attempts (specs US-SC-2: 1 per venue per 20 min, 6 per hour) are dropped
  before they become rows, and counted in `manifest.json`.
- Against truth: honest crowd MAE ≤ 0.6, gamer/shill MAE ≥ 1.2 *(placeholders)*.

**LS-4 Scout engagement and drop-off (coursework).**
- Scouts join in weekly cohorts. Each has a latent engagement that decays weekly and
  is bumped by points, bounty wins and streaks (v2 §B). When it drops below a
  threshold the Scout stops; that date is `syn_scout_truth.churned_at`.
- Observable churn label (coursework, CONTRACTS v2.1 §B): no report in 21 days.
- Targets *(placeholders)*: 40–60% of everyone who joined has churned by Nov 14;
  week-4 retention per cohort 35–60%; gamers churn or get removed faster than honest
  Scouts with bounty wins.
- `syn_scouts.last_active_at` = time of their last report (null if they never reported).

**LS-5 Status, points and reputation per specs §7.**
- Report `status`: `flagged` when specs §7.3 velocity (> 15 km/h) or outlier
  (|crowd − consensus| ≥ 2.5 with ≥ 3 others in ±20 min) fires; `disputed` /
  `removed` from `syn_disputes`; otherwise `accepted`. `pending` is never stored; it
  is derived at replay time (< 30 min old at `now`, see LS-8).
- `syn_points_ledger` has one row per specs §7.2 event (+10 accepted, +5 verified,
  +5 first at venue tonight, + bounty points, clawback −10) and sums to
  `syn_scouts.points`. Levels: Rookie 0, Regular 100, Insider 500, Legend 1500.
- Reputation follows specs §7.1 (start 0.5; consensus update ±0.05·(a − 0.7);
  +0.005 verified; −0.10 dispute upheld; clip 0.05–0.98), applied in time order.
  `syn_scouts.reputation` is the value at the end of Sat Nov 14.

**LS-6 Gaps and nulls.**
- `cover_usd` null in ~60% and `music_genre` null in ~40% of reports *(placeholders)*.
- ≥ 20% of venue × 30-min slots between 21:00 and 02:00 have no report; some venues
  have no report on some nights. Missing values are never filled with favourable defaults.

**LS-7 Operators, users, demand, disputes, bounties.**
- `is_claimed = 1` for ~50% of venues *(placeholder)*. Claimed venues post 0–2
  updates per night (cover, DJ, genres, event, offer + expiry); ~10% disagree with
  what Scouts see.
- `syn_users.prefs_json` matches the Preferences JSON in CONTRACTS.md.
- `syn_venue_events` (view, tap, save, recommend_impression) follows user sessions
  and venue busyness, so the owner dashboard's `demand_by_hour` has a shape.
- `syn_disputes`: owners of claimed venues dispute ~3% of reports at their venue,
  biased to unflattering ones; upheld ~30%, rejected otherwise, auto-rejected after 48 h.
- `syn_bounties` follow specs §7.5: checked every 15 min 21:00–02:00, created when
  confidence < 0.30 and no open bounty, points = 20 + 10·min(3, floor(freshness/30))
  (null freshness → 50), expire after 60 min, max 8 open. Claimed implicitly by the
  first accepted, verified report at that venue before expiry (`claimed_at`, `claimed_by`).
- `syn_feedback` ratings correlate with how well a venue's *true* state fit the user's
  prefs (Spearman ≥ 0.3 *(placeholder)*), so a good recommender can beat a random one.

**LS-8 Replay at `now=`.**
- `python -I -m simulator replay --now 2026-11-14T23:30:00-05:00` prints per venue:
  visible reports in the last 180 min, live offers, open bounties.
- `simulator.replay.visible(tables, now)` returns only what the app could know at
  `now`: reports with `ts ≤ now + 2 min` (specs cutoff), status shown as `pending` if
  < 30 min old and not flagged, disputes opened ≤ now, bounties created ≤ now and
  not expired or claimed, offers not expired, ledger entries ≤ now.
- `--shift-to 2026-11-17` re-dates the demo night (keeping time of night) into
  `data/synthetic_live/shifted/` for a "tonight" live demo; still marked synthetic.
- At `DEMO_NOW`: ≥ 25 of 35 venues have a report in the last 60 min and ≥ 3 bounties
  are open *(placeholders)*.

**LS-9 Shared genre vocabulary.**
- `simulator/config/genres.json` = `{"version": 1, "genres": [...]}` with exactly the 17
  slugs in CONTRACTS v2.1 §E: hip-hop, r&b, afrobeats, latin, reggaeton, house, techno,
  edm, disco, pop, top-40, throwbacks, indie, rock, punk, jazz, soul-funk.
- `simulator/genres.py` loads it and exports `GENRES` and `is_genre(s)`. Every genre the
  simulator writes is in it; validation fails otherwise. Changing it needs a contract change.

**LS-9b Demo-night snapshots (tableau, v2.2 §J).**
- `data/synthetic_live/demo_night_snapshots.csv`: `venue_id, snapshot_ts, crowd, dancing,
  line_minutes, vibe_score, confidence, n_reports, is_synthetic`; one row per venue per
  30 min from Sat 2026-11-14 20:00 to Sun 03:00 (15 × 35 = 525 rows).
- Values are the Live Venue State at `snapshot_ts`, from `recs.live_state.compute_all`
  if importable, else the simulator's specs §5 fallback (marked `# SYNTHETIC:` and
  recorded in `manifest.json` as `snapshot_source: recs|fallback`). Null stays null.
- Small enough to commit, so tableau can use it without running the simulator.

**LS-10 Deterministic and swappable.**
- Same seed and config give identical SHA-256 per CSV (test enforced); a different
  seed changes them.
- `manifest.json`: seed, config hash, git commit, generator version, row counts,
  sha256 per file, rate-limited attempts dropped.
- `docs/synthetic/live-sim.md` lists each table with what it imitates, how it is
  generated, the real table that replaces it, and swap steps.

## 6. Scope

**MVP (pushed by Fri 2026-11-13 18:00 ET, v2 §I)**, in priority order:
1. venue inputs extract, attributes, true state, scouts + reports with status,
   reputation + reputation history, points ledger, bounties, the build command into
   `data/live_sim.db`, demo-night snapshots, replay, validate;
2. venue updates, users, feedback;
3. venue events (owner dashboard demand) and disputes;
4. extracts for tableau, registry and workstream docs.

If time runs short, items in 3 ship with simpler rules (e.g. events = Poisson by hour)
rather than being dropped, because backend's owner dashboard needs them.

**Later**
- `stream` mode posting to `POST /api/reports` at N× speed for a live-updating demo.
- Feedback that uses `recs.scoring.recommend` instead of the placeholder chooser.
- All zip-10002 venues, then all `v_bars`; special-night configs.
- Calibrate curves against real pilot data.

## 7. Requirements

### 7.1 Inputs
- `simulator/data/venue_inputs.csv` (committed, real public data, `is_synthetic=0`),
  produced once by `python -I -m simulator extract-inputs` from `data/launch_venues.csv` +
  `venue_features` + `osm_venues`: `license_id, name, lat, lon, osm_amenity,
  osm_closes_late, liquor_tier, cuisine, noise_complaints, density_100m, opening_hours`.
  Loaders alias `license_id AS venue_id` (v2 §D).
- `data/venue_attributes_manual.csv` if present (team-filled, `is_synthetic=0`, same
  columns as `syn_venue_attributes`). The simulator uses its values when generating
  true state, so simulated reports agree with hand-labelled facts. It still writes
  synthetic rows for all 35 venues; backend prefers manual rows.
- `simulator/config/default.json`: every tunable number, each with a `_note`.

### 7.2 Venue attributes
- Style: OSM `nightclub` → `club`, `pub` → `pub`; name keywords (BALLROOM, CLUB →
  `club`; COCKTAIL, ROOM → `cocktail`; LOUNGE → `lounge`; WINE, CAFE, GROCERY →
  `restaurant-bar` or `lounge`); non-American/Other cuisine → `restaurant-bar`;
  otherwise priors dive 35%, cocktail 25%, lounge 15%, pub 10%, restaurant-bar 10%,
  club 5% *(placeholders)*. All 35 are Bar/Tavern licences (v2 §D), so clubs and
  dance floors are expected to be sparse.
- `has_dance_floor`: club 0.8, lounge 0.25, dive 0.15, others 0.05 *(placeholders)*.
- `capacity`: club 150–400, others 40–150; `typical_cover_usd` 0 unless club or
  dance floor, then 10–30 in steps of 5; `price_level` 1–4 by style and liquor tier.
- `genres`: 1–3 from `GENRES` via a style menu (e.g. dive: rock, punk, throwbacks,
  indie; club: hip-hop, house, techno, reggaeton, afrobeats, top-40; cocktail/lounge:
  jazz, soul-funk, disco).
- `opening_hours` copied from OSM when present, else null. `is_claimed` drawn ~50%.
- Hidden `popularity` (from log `noise_complaints` + noise) scales demand; it goes
  only into true state, never into contract tables.

### 7.3 True state (`syn_true_state`, evaluation only)
- Per venue per 15-min slot, 20:00–03:00: `occupancy = capacity × curve_style(t) ×
  weekday × night_shock × venue_night_shock × popularity × event_boost`, AR(1)
  noise between slots, 0 when closed.
- Style peaks *(placeholders)*: dive 23–01, cocktail 21–23, club 00–02, lounge
  22–00, pub 21–23, restaurant-bar 20–22. Weekday Thu 0.70, Fri 0.95, Sat 1.00.
  Night shock lognormal σ 0.15, venue-night σ 0.20. Holidays: Sat Sep 5 (Labor Day weekend)
  ×1.15, Sat Oct 31 (Halloween) ×1.3.
- Mapped to contract scales: crowd 1–5 from occupancy-fraction bins (< 0.2, 0.45,
  0.7, 0.9); dancing 0/1/2 from dance floor, occupancy and hour; line minutes when
  occupancy > 85% of capacity; cover after 22:00 or on events; genre from venue
  genres, rotating on DJ nights.

### 7.4 Scouts (`syn_scouts`, `syn_scout_truth`)
- ~150 Scouts ever join *(placeholder)*: 50 in week 1, 5–15 per later week.
- Latent engagement `e`: starts ~Beta(4, 3); weekly `e ← 0.85·e + bumps`
  (+0.05 per 50 points, +0.08 per bounty win, +0.03 for a 2-week streak, −0.05 for a
  flagged/removed report) *(placeholders)*; churn when `e < 0.25`; 5% chance of a
  one-time return after ≥ 3 weeks away.
- Active nights per week ~ Poisson(1.5·e) capped at 3; venues per night 1–4 chosen
  by distance and style taste; stay 30–90 min; report on arrival, sometimes again
  (respecting the 20-min/venue and 6/hour limits; violations dropped).
- Observation model per archetype: σ for crowd/dancing/line, bias, presence
  probability (honest 0.9, gamer 0.3), `distance_m` when present 0–150 m, otherwise
  151–3000 m or null (GPS denied ~15%).
- `syn_scout_truth` (v2.1 §E): `scout_id, archetype, home_venue_id (shills only),
  true_accuracy (crowd σ), cohort_week (1–12), churned_at (null if still active),
  is_synthetic`.
- `syn_scout_reputation_history` (v2.1 §E): `scout_id, as_of_date, reputation, points,
  level, is_synthetic`, one row per scout per night they were active, written by the
  same time-ordered pass that sets final `syn_scouts.reputation`.
- `syn_scouts`: display names from a fixed word list (no real people), `joined_at`,
  `reputation`, `points`, `level`, `reports_count`, `last_active_at`.

### 7.5 Reports (`syn_scout_reports`)
- Columns per CONTRACTS + v2: `status` and `distance_m`. `verified_presence = 1`
  iff `distance_m ≤ 150` (specs presence radius). Raw GPS is never generated or stored.
- `status` from specs §7.3–7.4 applied by a post-pass in time order (velocity,
  outlier, then disputes).
- IDs `syn-r-000001…` assigned after a deterministic sort by (ts, venue_id, scout_id).

### 7.6 Bounties (`syn_bounties`) and the specs §5 fallback
- Specs §7.5 exactly (see LS-7). Confidence, freshness and vibe come from
  `recs.live_state.compute` if importable, else from `simulator/_live_state.py`, a
  minimal copy of specs §5.1–5.7 tested against golden vector G1 (vibe 65,
  conf 0.67). Marked `# SYNTHETIC: mirror of specs §5; delete when recs is importable`.
  The same function fills `demo_night_snapshots.csv`.
- Because bounties change where Scouts go, reports and bounties are generated slot by
  slot in one loop per night.

### 7.7 Updates, users, events, disputes, feedback, ledger
- `syn_venue_updates`: claimed venues, 17:00–22:00 posts, offers expire 1–3 h later.
- `syn_users`: 300 *(placeholder)*; home locations from a mixture centred on the LES
  plus other Manhattan/Brooklyn spots; prefs from personas (dancers, cocktail-chill,
  cheap-dive, live-music, big-group) with genres from `GENRES`.
- `syn_venue_events`: per user-night session, impressions → taps → saves with
  funnel rates *(placeholders: tap 25% of impressions, save 10% of taps)*, more at
  busier venues; ~30% anonymous (`user_id` null). Volume capped (~150k rows).
- `syn_disputes`: `opened_by` = owner pseudo-ID `syn-o-<venue_id>`; reasons from a short list.
- `syn_feedback`: placeholder chooser over true state (top 5 by fit + noise),
  `visited` ~ Bernoulli(0.6), rating from fit + noise.
- `syn_points_ledger`: one row per points event; `report_id` / `bounty_id` set as applicable.

### 7.8 Outputs
- CSVs in `data/synthetic_live/` (gitignored by default; regenerated by the build
  command). Committed: `manifest.json`, `validation.json` (so anyone can check a rebuild
  matches by hash) and `demo_night_snapshots.csv` (525 rows, for tableau).
- `data/live_sim.db` (never committed), tables named exactly as the CSVs, indexes on
  `(venue_id, ts)` and `(scout_id, ts)`.
- `data/synthetic_live/extracts/hourly_by_style.csv` for tableau (hourly by style × weekday).
  Tableau's hourly cell for HH uses the HH:30 row of `demo_night_snapshots.csv` (v2.2 §J).
- Only `syn_` tables are written. Backend creates the empty real twin tables and, on
  Postgres, copies the `syn_` tables in (v2.2 §J).
- CSV total ≤ 30 MB *(placeholder)*.

### 7.9 Non-functional
- Python 3.13; pandas ≥ 3, numpy ≥ 2 (already required); pytest for tests. No new
  runtime dependencies.
- Full build < 60 s on a laptop CPU, memory ≤ 1 GB; test suite ≤ 60 s (uses `--nights 3`).

## 8. Dependencies on other workstreams

| Workstream | live-sim needs | live-sim gives |
|---|---|---|
| specs | §5 confidence/freshness, §7 status, points, levels, reputation, bounties, golden vector G1 (churn label is 21 days per CONTRACTS v2.1, overriding specs' 14) | simulated nights to evaluate those rules (gaming share, bounty load) |
| research | persona shares and preference ranges; drop-off assumptions | `simulator/config/genres.json` for `syn_interviews` / `syn_survey_responses` |
| tableau | chart list | `demo_night_snapshots.csv` (committed) + hourly extracts |
| live-sim | — | — |
| ml-recs | `recs.live_state` (optional: bounties and snapshots) | 36 nights; `syn_true_state`; `syn_scout_reputation_history`; holdout Nov 13–14 |
| backend | attaches `data/live_sim.db` (`LIVE_SIM_DB`) or copies it into Postgres; creates empty real twin tables | tables per v2 §E; `replay.visible` rules for `now=` |
| frontend | "demo data" badges | believable content at `DEMO_NOW` |
| coursework | none (label fixed at 21 days) | 12 weeks of Scout activity and `churned_at` |
| integration | calls exactly `python -I -m simulator --seed 42 --out data/live_sim.db` in `make data` and the Render build; merge slot after coursework | one deterministic command; outputs by Fri Nov 13 18:00 ET |

## 9. Success metrics

- All `validate` checks pass on seed 42 (100%).
- Determinism test passes.
- ml-recs crowd model beats the venue-hour baseline on the Nov 13–14 holdout by a
  believable margin (5–25% MAE improvement *(placeholder)*). A much larger gain means
  the simulator is too easy and needs more noise.
- Reputation- and status-weighted `live_state` has lower crowd error vs truth than
  unweighted (shows specs' anti-gaming checks matter).
- Churn: 40–60% of joined Scouts churned by Nov 14; observable 21-day label agrees
  with `churned_at` within 21 days for ≥ 80% of churners.
- At `DEMO_NOW`: ≥ 25/35 venues with a report in the last 60 min, ≥ 3 open bounties.
- Zero rows with `is_synthetic ≠ 1`; every inventing module has `# SYNTHETIC:` notes.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Circularity: models learn the simulator's own rules | Say so in every write-up; compare against baselines; keep noise realistic |
| Real, named bars shown with invented facts | `is_synthetic`, demo badge, registry disclaimer; manual file for real facts |
| Simulator's specs §5 fallback drifts from `recs` | Use `recs` when importable; G1 test; delete the copy after integration |
| DST fall-back on the Oct 31 night | UTC internally; dedicated test |
| Bounty ↔ report feedback loop makes generation slow or unstable | Slot-by-slot loop with a cap of 8 open bounties; runtime test |
| Deadline (Fri Nov 13 18:00) is tight | Priority order in §6; simpler fallbacks for events/disputes |
| Leakage: joining final `syn_scouts.reputation` to past reports | `syn_scout_reputation_history` (v2.1); registry and RULES say to join as of the report date |
| Full run misses the < 60 s build target | Vectorise truth and observations per night; profile the night loop; `--nights` for tests; runtime check in `validate` |
| Large `syn_venue_events` | Row cap; CSVs not committed |

## 11. Open questions

1. Tableau reads the committed `demo_night_snapshots.csv`; does it also want the hourly
   extract committed, or will it run the build?
2. Before ml-recs merges, snapshots come from the fallback. Should integration re-run
   the build after `recs/` lands so `snapshot_source = recs`? (Plan: yes, in `make data`.)
3. Will the team fill `data/venue_attributes_manual.csv` before Nov 13? The simulator
   works either way.
4. Specs still says 14 days for churn; CONTRACTS v2.1 says 21. Specs should update its PRD.
5. Persona shares from research: placeholders until it publishes.

## 12. Contract change requests (for master; CONTRACTS.md is not edited here)

All earlier requests were resolved in v2–v2.2 (window, genres, truth tables,
reputation history, bounty columns, IDs). Remaining:

1. **Owner pseudo-IDs**: `syn_disputes.opened_by` for owners uses `syn-o-<venue_id>`
   until backend's demo-login issues owner IDs. Confirm the format.
