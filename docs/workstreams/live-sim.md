# live-sim: as built (Nov 17, 2026)

Branch `nightlife/live-sim`. Owns `simulator/`, `data/synthetic_live/`, writes `data/live_sim.db`.
Everything it produces is synthetic (`is_synthetic = 1`). Registry: `docs/synthetic/live-sim.md`.

## How to run

```bash
python -m simulator --seed 42 --out data/live_sim.db          # fixed build, 36 nights, ~7 s
python -m simulator --seed 42 --out data/live_sim.db --nights 3   # quick mode (last 3 nights, ends Sat Nov 14)
python -m simulator validate                                  # re-check CSVs in data/synthetic_live/
python -m simulator replay --now 2026-11-14T23:30:00-05:00 [--venue <license_id>]
python -m simulator replay --shift-to 2026-11-17               # demo night re-dated -> data/synthetic_live/shifted/
python -m simulator extract-inputs                            # only to refresh simulator/data/venue_inputs.csv
python -m pytest simulator/tests -q                           # 27 tests, ~6 s
```
Run from the repo root (CONTRACTS f5c95d2: no `-I`). Also works: `python -I simulator ...` (directory form),
or `pip install -e ./simulator` and then `python -I -m simulator ...` from anywhere.

The build: generate → write 13 CSVs + `demo_night_snapshots.csv` + `extracts/hourly_by_style.csv` →
load `data/live_sim.db` (only `^syn_[a-z_]+$` tables; refuses a target named `manhattan_bars.db`) →
`validation.json` + `manifest.json`. Exit code 1 only on hard failures (schema, foreign keys, genres,
synthetic flags, ledger, presence rule, churn ordering); realism misses are reported but don't break a deploy
(`--strict` makes any failure exit 1). It does not need `data/manhattan_bars.db`.

## What was built
- `simulator/config/genres.json`: the shared 17-slug vocabulary (v2.1 §E), loaded as `config.GENRES`.
- Stages, each with its own seeded RNG (sha256 of the stage name): `venues` → `updates` → `truth` →
  `nightloop` (scouts + reports + bounties, slot by slot) → `trust` (status, disputes, reputation, points,
  history) → `users` → `events` → `feedback`.
- `_live_state.py`: specs §5.1–5.7 mirror (passes golden vector G1: vibe 65, conf 0.67). `replay.live_states`
  prefers `recs.live_state.compute_all` when importable and falls back otherwise; manifest says which.
- `replay.visible(tables, now)`: rows with `ts ≤ now + 2 min`; status derived at `now` (`pending` if < 30 min
  and not flagged, `disputed` while a dispute is open, `removed` once upheld); expired offers blanked; bounties
  claimed after `now` shown as open; `open_bounties`; reputation history only for completed nights.
- Validation on seed 42 (all green): report peak 22:00–01:00 on 94% of nights; Sat ≥ Fri ≥ Thu at 23:00;
  01:00 club/dive > cocktail/restaurant-bar and the reverse at 20:30; honest crowd MAE 0.21, gamer 1.97,
  shill 1.32; ≥ 20% empty venue-slots; cover/genre null ~0.6/0.4; churn 55.5%, week-4 retention 56%,
  21-day label vs latent churn 88%; feedback Spearman ≥ 0.3; at DEMO_NOW 31 venues fresh in the last
  60 min, 8 open bounties, pending reports present; CSVs 11 MB; build 7 s.

Row counts (seed 42): reports 8,147 (~226/night), scouts 209, bounties 2,409, ledger 17,702, events 65,973,
updates 662, disputes 250, feedback 1,440, users 300, true state 35,420, snapshots 525.

## Consumers
- **backend**: attach `data/live_sim.db` (`LIVE_SIM_DB`), or copy the `syn_` tables into Postgres. Use
  `simulator.replay.visible` semantics for `now=`. Column order = CONTRACTS base, then v2 additions, with
  `is_synthetic` last (see `simulator/schema.py`).
- **ml-recs**: holdout = nights 2026-11-13 and 2026-11-14; join reputation from
  `syn_scout_reputation_history` as of the report's night (not final `syn_scouts.reputation`).
  `simulator.generate(simulator.config.load("default", seed=42))` gives the tables in memory.
- **tableau**: committed `data/synthetic_live/demo_night_snapshots.csv` (hour HH = the HH:30 row) and
  `extracts/hourly_by_style.csv` (built, not committed).
- **coursework**: `syn_scouts`, `syn_scout_reports`, `syn_points_ledger`, `syn_scout_reputation_history`,
  `syn_scout_truth.churned_at`; churn label = no report in 21 days.

## Assumptions (recorded per the build instructions; no owner answers received)
1. Deadline moved: built on demo day (Nov 17), MVP first. No Render/Vercel accounts; nothing merges to main.
2. Venue attributes stay synthetic; `data/venue_attributes_manual.csv` is supported if the team fills it.
3. No real interviews or pilot data, so every behavioural number is a placeholder (`_note` per config section).
4. Scout population is ~209 (60 in week 1, 8–18 per later week) rather than ~150: needed to reach ≥ 25
   fresh venues at DEMO_NOW with ~50% churn. Volume is ~226 reports/night (plan said 300–700).
5. Config notes are one `_note` per section instead of per key (time).
6. Bounty claims are made in the loop by the first verified, not-velocity-flagged report; the bounty pays
   (ledger row) only if that report is still accepted/disputed after the trust pass (specs §7.3.6). In the
   loop, confidence uses reputation 0.5 and provisional status.
7. Engagement bumps use provisional points inside the loop; the official ledger is computed after.
8. Flagged reports get their award rows and then, 30 min later, a clawback and a −10 penalty, so the ledger
   shows the full story; upheld disputes do the same at `resolved_at`.
9. `churned_at` = end of the week in which engagement fell below the threshold; scouts who returned and are
   active at the end have `churned_at = null`.
10. Dispute `status` values: `open|upheld|rejected|auto_rejected` (contract doesn't list them). Stored report
    status `disputed` only for disputes still open at the end of the data (Sun Nov 15 03:00).
11. OSM `opening_hours` parsed with a small parser; unknown → open all night. THE BACK ROOM's OSM hours omit
    Saturday, so it is closed on Saturdays here (real data, not a bug).
12. `syn_venue_events` uses the PRD's simpler fallback (Poisson by slot × busyness), not user sessions.
13. Night grid: 15-min slots in elapsed time from 20:00 local; the Oct 31 night has 32 slots (DST fall-back).

## Known limits / open issues
- Circularity: models trained on this data learn the simulator's rules. Say so in any write-up.
- `snapshot_source` is `fallback` until `recs` is importable from the build; re-run the build after recs merges.
- Week-4 retention is 0.56–0.67 depending on seed (target 35–60%); seed 42 passes.
- `stream` mode (post to `POST /api/reports`) and feedback via `recs.scoring.recommend` are not built (later).

## Contract change requests
- **CCR-1 (build command)**: resolved by CONTRACTS f5c95d2 (`python -m simulator ...` from the repo root,
  no `-I`). The `-I` forms still work via `python -I simulator ...` or after `pip install -e ./simulator`.
- **CCR-2 (owner pseudo-IDs)**: `syn_disputes.opened_by` uses `syn-o-<venue_id>` until demo-login issues owner IDs.
- **CCR-3 (column order)**: v2 additions are placed before `is_synthetic` (which stays last) in every table.
- **CCR-4 (dispute status enum)**: `open|upheld|rejected|auto_rejected`.
