# PRD: live-sim (time-based synthetic nightlife simulator)

Workstream: `live-sim` · Branch: `nightlife/live-sim` · Owns: `simulator/`, `data/synthetic_live/`
Status: planning (no code yet) · Written: 2026-11-11 · Contract: `docs/CONTRACTS.md`

Numbers marked *(placeholder)* are reasoned guesses to be tuned during the build,
not measured facts.

## 1. Problem

Nightlife Autopilot ranks venues by what is happening *right now*: crowd, dancing,
line, cover, music. None of that exists in the public pipeline. The database has
5,737 licensed venues with licenses, inspections, 311 complaints and OSM tags, but
no scouts, no reports, no users, no operator posts and no outcomes. Without live-like
data:

- `ml-recs` has nothing to compute Live Venue State from and nothing to train or
  validate the crowd model on.
- `backend` has empty tables behind every live endpoint.
- `frontend` can only show static mockups.
- `tableau` has no hourly patterns to chart.
- The Nov 17 integration demo ("working model, deployed") has no night to show.

We need one reproducible source of fake-but-plausible nightlife activity for the 35
LES launch venues. It should cover realistic Thu–Sat nights, include messy and
dishonest reporters, carry a hidden ground truth so models can be scored, and be
easy to delete and replace once real Scout data arrives.

## 2. Goals

1. Generate every `syn_` table in CONTRACTS.md (`syn_venue_attributes`, `syn_scouts`,
   `syn_users`, `syn_scout_reports`, `syn_venue_updates`, `syn_feedback`,
   `syn_bounties`), matching the contract schemas column for column.
2. Make it time-based: reports follow hourly arrival curves that vary by venue style,
   weekday and night-level shocks over Thu–Sat nights (18:00–04:00 America/New_York).
3. Model reporter behaviour: honest, casual, sloppy, gaming and shill scouts, plus
   missing optional fields and coverage gaps.
4. Keep a hidden ground truth (true venue state every 15 minutes, true scout
   archetype) so `ml-recs` can measure how well `live_state` recovers reality.
5. Be deterministic: same seed and config give byte-identical outputs.
6. Ship a CLI that generates, validates, loads into SQLite as `syn_` tables, and
   replays a night at any `now=` for demos.
7. Follow the synthetic-data rule completely: `is_synthetic=1`, `syn_` prefix,
   `# SYNTHETIC:` comments, and a registry in `docs/synthetic/live-sim.md`.

## 3. Non-goals

- Not a recommender, scorer or Live Venue State calculator. `ml-recs` owns those.
  live-sim only produces the raw events they consume.
- No HTTP API. `backend` serves the data; live-sim provides files, tables and a
  Python helper.
- No claims about real venues. Attributes assigned to real, named LES bars (genres,
  dance floor, cover) are guesses and must never be shown without the "demo data" badge.
- Not a statistical twin of real Scout data. We have none to fit against, so
  realism comes from stated rules (section 7), not from fitting.
- No changes to `src/`, the public tables in `data/manhattan_bars.db`, or `CONTRACTS.md`.
- No venues beyond the 35 launch venues in MVP (the generator takes a venue list, so
  this can grow later).

## 4. Users of this workstream

| User | What they need from live-sim |
|---|---|
| ml-recs (Python) | reports + updates over many nights to build `live_state`; hourly ground truth for crowd-model training and temporal validation; scout archetypes to test anti-gaming weighting |
| backend | CSVs / `syn_` tables to load; a defined `now` filter for replay; seeded IDs |
| frontend | believable cards, leaderboard, bounties and offers on the demo night |
| tableau | hourly crowd and report-volume extracts by style and weekday |
| coursework | user and scout activity history that could feed the churn exercise |
| integration | one pinned seed and demo night that every piece agrees on |
| Ryan / graders | a clear story of what is fake, why it is plausible and how to swap it |

## 5. User stories and acceptance criteria

**LS-1 Generate a season.** As ml-recs, I want several weekends of Thu–Sat nights so
I can train on early nights and test on later ones.
- `python -I -m simulator generate --seed 42` writes all 7 contract tables plus the
  2 truth tables to `data/synthetic_live/` in under 60 s *(placeholder)* on a laptop.
- Default window: 4 weekends, Thu 2026-10-22 to Sat 2026-11-14, 12 nights *(placeholder)*.
- Every row has `is_synthetic = 1`. Columns and order match CONTRACTS.md exactly.

**LS-2 Realistic nightly rhythm.** As tableau and ml-recs, I want report volume and
true crowd to rise and fall plausibly.
- Report volume across all venues peaks between 22:00 and 01:00 on every night.
- Mean true crowd on Saturday ≥ Friday ≥ Thursday at 23:00.
- At 01:00, `club`-style venues have higher mean true crowd than `cocktail` and
  `restaurant-bar` venues; at 20:00 the order flips.
- Validation (`simulator validate`) checks and reports each of these.

**LS-3 Messy reporters.** As ml-recs, I want bad scouts in the data so
reputation weighting has something to catch.
- Scout archetypes (hidden in `syn_scout_truth`): honest, casual, sloppy, gamer,
  shill, in fixed shares (section 7.3).
- Measured against truth, honest-scout crowd MAE ≤ 0.6 and gamer/shill crowd
  MAE ≥ 1.2 *(placeholders)*, checked by validation.
- Gamers produce report bursts (≥ 4 reports in 10 min) and low `verified_presence`.

**LS-4 Gaps and nulls.** As ml-recs and frontend, I want missing data so that
"null, not a favourable default" and the confidence score get exercised.
- `cover_usd` null in ~60% and `music_genre` null in ~40% of reports *(placeholders)*.
- ≥ 20% of venue × 30-min slots between 21:00 and 02:00 have no report.
- Some venues get no reports on a given night.

**LS-5 Operator activity.** As frontend and backend, I want official posts and offers.
- About half the launch venues are "claimed" and post 0–2 updates per night with
  cover, DJ, genres, event and offers with expiry.
- About 10% of updates disagree with what scouts see (stale cover, wrong genre), so
  scouts vs operator conflicts can be shown.

**LS-6 Users and outcomes.** As ml-recs, I want users with preferences and
post-visit feedback.
- `syn_users.prefs_json` validates against the Preferences JSON in CONTRACTS.md.
- `syn_feedback` ratings correlate with how well the venue's *true* state fit the
  user's prefs (Spearman ≥ 0.3 *(placeholder)*), so a good recommender can beat a
  random one.

**LS-7 Bounties.** As frontend, I want open and claimed bounties.
- Bounties are created at busy-but-unreported venues; some get claimed by a scout who
  then files a report within 30 min at that venue.

**LS-8 Load into SQLite.** As backend, I want the tables in a database.
- `simulator load --db <path>` creates or replaces only tables whose names start with
  `syn_`. It refuses to touch any other table (test enforced).
- Row counts in the DB equal the CSV row counts.

**LS-9 Replay a night.** As integration, I want to show "what the app saw at 23:30
on Saturday".
- `simulator replay --now 2026-11-14T23:30` prints per-venue counts of visible
  reports, live offers and open bounties at that moment.
- `simulator.replay.visible(tables, now)` returns only rows the app could know at
  `now` (reports with `ts <= now`, offers not expired, bounties created and not yet
  claimed). Backend can import it or copy its rules for `?now=`.
- `--shift-to 2026-11-17` re-dates the demo night so the Nov 17 live demo can say
  "tonight". Shifted output is written to a separate folder and still marked synthetic.

**LS-10 Reproducible and swappable.** As Ryan, I want to regenerate or delete
everything safely.
- Same seed and config give identical SHA-256 per CSV (test enforced).
- `manifest.json` records seed, config hash, git commit, generator version and row counts.
- `docs/synthetic/live-sim.md` lists each dataset with what it imitates, how it is
  generated, the real source that replaces it, and swap steps.

## 6. Scope

**MVP (by Nov 15 freeze, ahead of Nov 17 integration)**
- Venue attribute assignment for the 35 launch venues.
- Hidden true-state engine (15-min steps) with style curves, weekday factors and shocks.
- Scouts with archetypes, reports, presence flag, nulls and gaps.
- Venue updates and offers, bounties, users with prefs, feedback.
- CLI: `generate`, `validate`, `load`, `replay`; `--preset demo`.
- Truth tables, validation report, manifest, registry doc, workstream doc.

**Later**
- `stream` mode: post reports to a running backend (`POST /api/reports`) at N× speed
  so the demo updates live.
- More venues (all 10002, then all `v_bars`) using the same venue-list input.
- Special nights (holiday, weather, big concert at Bowery Ballroom) as config files.
- Feedback loop: plug `recs.scoring.recommend` in so feedback reflects what the app
  actually recommended.
- Synthetic owner demand metrics (views, taps) if the contract change below is accepted.
- Calibrate curves against real data once Scout reports, or public proxies such as
  Google Popular Times (terms permitting), exist.

## 7. Requirements

### 7.1 Inputs
- `data/launch_venues.csv` (35 rows; `license_id` = `venue_id`).
- Read-only joins to `venues` and `venue_features` in `data/manhattan_bars.db`:
  `osm_amenity`, `osm_closes_late`, `liquor_tier`, `cuisine`, `noise_complaints`,
  `density_100m`, `lat`, `lon`.
- Config file `simulator/config/default.json` (all tunable numbers live here, none
  hard-coded in logic).

### 7.2 Venue attributes (`syn_venue_attributes`)
- Style comes first from rules, then from a hand-editable override file:
  `osm_amenity = nightclub` → `club`; `pub` → `pub`; name contains BALLROOM / CLUB
  → `club`; COCKTAIL / LOUNGE / ROOM → `cocktail` or `lounge`; WINE / CAFE / GROCERY
  → `restaurant-bar` or `lounge`; `cuisine` not American/Other → `restaurant-bar`;
  otherwise drawn from priors (dive 35%, cocktail 25%, lounge 15%, pub 10%,
  restaurant-bar 10%, club 5% *(placeholders)*). Then
  `simulator/config/venue_style_overrides.csv` applies team guesses.
- `has_dance_floor`: club 0.9, lounge 0.3, dive 0.2, others 0.05 *(placeholders)*.
- `capacity`: club 150–400, others 40–150, scaled by `density_100m`.
- `typical_cover_usd`: 0 unless club or dance floor; then 10–30 in steps of 5.
- `genres`: 1–3 from a style-dependent menu (hip-hop, r&b, house, techno, latin,
  pop, indie, rock, jazz, top-40), pipe-separated.
- `price_level` 1–4 by style and `liquor_tier`.
- A hidden `popularity` factor per venue (from log `noise_complaints` plus noise,
  standardised) scales demand. It goes into the truth table, not the contract table.

### 7.3 Scouts (`syn_scouts`, hidden `syn_scout_truth`)
- 60 scouts *(placeholder)*. Archetype shares: honest 55%, casual 25%, sloppy 10%,
  gamer 6%, shill 4%.
- Per archetype: nights active per weekend, reports per visit, observation noise σ
  per field, presence probability, bias (shill: +2 crowd at its "home" venue; gamer:
  random venues, bursts, copies of the last report).
- `reputation`, `points`, `level`, `reports_count` are computed after reports exist,
  using placeholder rules (10 pts/report, bounty points, reputation = smoothed
  agreement with truth). The rules are labelled `# SYNTHETIC:` until `specs`
  publishes the real formulas.

### 7.4 True state and reports
- True state per venue per 15-min step: `occupancy = capacity × curve_style(hour) ×
  weekday_factor × night_shock × venue_night_shock × popularity`, with AR(1) noise
  between steps.
- Mapped to contract scales: crowd 1–5 from occupancy fraction bins; dancing 0/1/2
  from dance floor, occupancy and hour; line minutes when occupancy > 85% of
  capacity *(placeholder)*; cover from typical cover after 22:00 and on events;
  genre from venue genres (rotating on DJ nights).
- Reports: scouts pick 1–4 venues per active night, walking order by distance and
  style taste, staying 30–90 min, reporting on arrival and sometimes again.
  Observations = truth + archetype noise/bias, rounded and clipped.
- Timestamps are ISO 8601 with the America/New_York offset. Generation runs in UTC
  internally. The Oct 31 → Nov 1 night crosses the DST fall-back (01:00–02:00
  repeats) and must produce valid, ordered timestamps.
- IDs are deterministic strings with a `syn-` prefix (e.g. `syn-r-20261114-000123`).

### 7.5 Updates, users, feedback, bounties
- Updates: claimed venues post between 17:00 and 22:00; offers expire 1–3 h later;
  10% stale or wrong.
- Users: 300 *(placeholder)*. Home locations from a mixture centred on the LES plus
  other Manhattan/Brooklyn spots. Prefs drawn from personas (dancers, cocktail-chill,
  cheap-dive, live-music, big-group). Persona shares come from `research` when ready.
- Feedback: per user-night, a simple built-in placeholder chooser picks a venue from
  the top 5 by fit to *true* state plus noise, then visited ~ Bernoulli(0.6) and
  rating from fit + noise. Marked `# SYNTHETIC:` and replaceable by `recs.scoring`.
- Bounties: every 30 min from 21:00 to 02:00, venues with expected crowd ≥ 3 and no
  report in 60 min may get a bounty (20–50 pts). Claimed when a scout reports there
  within 30 min.

### 7.6 Outputs
- `data/synthetic_live/<table>.csv` for 7 contract tables + `syn_true_state.csv`,
  `syn_scout_truth.csv`, `manifest.json`, `validation.json`.
- Total size ≤ 20 MB *(placeholder)*. CSVs are committed; the modified `.db` is not.

### 7.7 Non-functional
- Python 3.13, pandas ≥ 3, numpy ≥ 2 (already in `requirements.txt`). pytest for
  tests. No new runtime dependencies.
- Runtime ≤ 60 s for 12 nights × 35 venues; memory ≤ 1 GB.
- Pure functions per stage, so ml-recs can import `simulator` in notebooks.

## 8. Dependencies on other workstreams

| Workstream | live-sim needs from them | live-sim gives them |
|---|---|---|
| specs | style enum confirmation; points, level and reputation formulas; half-life (to set report spacing that tests decay); confidence display threshold | ground truth for checking those rules against simulated nights |
| research | persona shares and preference ranges for users; scout behaviour assumptions from interviews; typical cover and line ranges | a data dictionary for synthetic interview data to stay consistent with |
| tableau | chart list, to decide which extracts help most | hourly crowd and report-volume CSVs by style and weekday |
| ml-recs | agreement on truth-table format; later, `recs.scoring.recommend` for the feedback loop | reports, updates, truth for `live_state` evaluation and crowd-model temporal validation (train Oct 22–Nov 7, test Nov 12–14) |
| backend | DB path and whether `syn_` tables go into `manhattan_bars.db` or a separate file; `now=` semantics | loadable tables, `replay.visible()` rule, seeded IDs |
| frontend | where "demo data" badges go | believable demo-night content (leaderboard, offers, bounties) |
| coursework | whether churn exercise wants scout/user activity | activity history per scout and user across nights |
| integration | demo date/time and pinned seed | `--preset demo`, frozen outputs and a demo script |

## 9. Success metrics

- All `simulator validate` checks pass on the pinned seed (target 100%).
- Determinism test passes: identical hashes across two runs.
- ml-recs crowd model beats the venue-hour-average baseline on held-out nights, but
  by a believable margin: MAE improvement 5–25% *(placeholder)*. A much larger gain
  means the simulator is too easy and should get more noise.
- Reputation-weighted `live_state` has lower crowd error vs truth than unweighted
  (shows anti-gaming matters).
- Demo replay at Sat 23:30 shows ≥ 25 of 35 venues with a fresh report (≤ 60 min)
  and ≥ 3 open bounties *(placeholders)*.
- Zero untagged synthetic rows or files (checked by validation and by grep for
  `# SYNTHETIC:` in every module that invents numbers).

## 10. Risks

| Risk | Mitigation |
|---|---|
| Circularity: models learn the simulator's own rules, so metrics look better than reality | Say so in every write-up; report gains against a baseline; keep noise realistic; never present simulated accuracy as real-world accuracy |
| Real, named bars shown with invented facts (dance floor, cover, "packed") | `is_synthetic` on every row, demo badge in UI, disclaimer in registry; no export outside the class |
| DST fall-back on Nov 1 breaks timestamps or ordering | Generate in UTC, convert at write time, dedicated test for the Oct 31 night |
| Writing to the shared `manhattan_bars.db` breaks the pipeline or bloats git | `load` only touches `syn_*` tables (tested); the modified DB is not committed; option to load into a separate DB |
| Specs formulas land late | All rule numbers live in config with `# SYNTHETIC:` placeholders; swap without code changes |
| Contract change requests not accepted | Truth tables are separate files, not served; the contract tables stay exact either way |
| Scope creep (stream mode, more venues) before Nov 17 | Marked "Later"; MVP freeze Nov 15 |

## 11. Open questions

1. Should `syn_` tables load into `data/manhattan_bars.db` (default in this plan) or a
   separate `data/synthetic_live/live_sim.db`? Backend and integration decide.
2. Will the contract accept the evaluation-only tables `syn_true_state` and
   `syn_scout_truth`, and the extra bounty columns (see Contract change requests)?
3. May the team hand-label the 35 venues' style and genres from public knowledge? That
   would be more realistic, but those rows would then be "manual estimates" rather
   than purely synthetic. Plan: keep `is_synthetic=1` and add a note.
4. Demo night and time: plan assumes Sat 2026-11-14 23:30, shifted to Tue 2026-11-17
   for the live demo. Confirm with integration.
5. Points, levels and reputation formulas: placeholders until `specs` publishes them.
6. Number of weekends: 4 is enough for one temporal split. Does ml-recs want more?
7. Who owns synthetic owner-dashboard demand (views, taps)? This plan proposes
   live-sim (new table, see below).

## 12. Contract change requests (for integration; CONTRACTS.md is not edited here)

1. **Add `syn_true_state`** (evaluation only, never served by the API): `venue_id, ts,
   crowd_true (float 1–5), dancing_true (float 0–2), line_minutes_true,
   cover_usd_true (nullable), genre_true (nullable), occupancy, is_synthetic`.
2. **Add `syn_scout_truth`** (evaluation only): `scout_id, archetype
   (honest|casual|sloppy|gamer|shill), home_venue_id (nullable), is_synthetic`.
3. **Extend `syn_bounties`** with `expires_at` and `claimed_at` (both nullable) so
   `now=` replay can tell open from expired or claimed bounties.
4. **Add `syn_venue_demand`** for the owner dashboard: `venue_id, ts (hourly), views,
   taps, saves, is_synthetic`.
5. **ID convention:** synthetic primary keys start with `syn-` so they never collide
   with real IDs after swap.
6. **Add `is_claimed` (0/1) to `syn_venue_attributes`** so frontend knows which venues
   have an operator profile.
