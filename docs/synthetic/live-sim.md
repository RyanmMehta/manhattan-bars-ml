# Synthetic data registry: live-sim

**Every row listed here is synthetic (`is_synthetic = 1`).** None of it describes what really happens at
these bars. The venues are real (SLA licences, public data), but their attributes, crowds, Scouts, users and
outcomes are invented. Show the "demo data" badge wherever any of it appears.

Built by `python -I -m simulator --seed 42 --out data/live_sim.db` (needs `pip install -e ./simulator` once;
no-install form: `python -I simulator --seed 42 --out data/live_sim.db`). Seed 42 gives byte-identical CSVs (sha256 in
`data/synthetic_live/manifest.json`). CSVs go to `data/synthetic_live/` (gitignored except the snapshots file);
the same tables are loaded into `data/live_sim.db` (never committed).

## General swap path (all app tables)
1. Real rows go into the same table without the `syn_` prefix (`scout_reports`, `venue_updates`, ...), which
   backend creates empty from day one (CONTRACTS v2 §E, v2.2 §J).
2. Backend reads `syn_X UNION ALL X`; set `INCLUDE_SYNTHETIC=0` to hide synthetic rows.
3. Once real data is enough, stop running the build command and drop `data/live_sim.db`.

## Tables

Rows are for seed 42, full 36-night run (Thu 2026-08-27 → Sat 2026-11-14, 20:00–03:00 ET).

| File / table | Rows | Imitates | How generated (module, config keys) | Real source that replaces it |
|---|---|---|---|---|
| `syn_venue_attributes` | 35 | style, genres, dance floor, cover, capacity, price, claimed, hours | `venues.py`; `venues.*` (style rules from name/OSM amenity + priors). `opening_hours` is **real** OSM text when present | `data/venue_attributes_manual.csv` (team-labelled, `is_synthetic=0`, overrides these rows in the simulation and in backend); operator profiles later |
| `syn_scouts` | 209 | Scout accounts: reputation, points, level, counts, last active | `scouts.py` (population) + `trust.py` (final stats); `scouts.*`, `specs.*` | backend `scouts` table (demo-login, then real auth) |
| `syn_users` | 300 | app users with saved prefs (`prefs_json` = CONTRACTS Preferences) | `users.py`; `users.personas`, `users.home_mix` | onboarding answers |
| `syn_scout_reports` | 8,147 | 10-second vibe checks with `status`, `distance_m` | `nightloop.py` (observations of true state with archetype noise, rate limits, presence) + `trust.py` (status); `scouts.obs`, `scouts.*_null_p`, `specs.*` | `POST /api/reports` → `scout_reports` |
| `syn_venue_updates` | 662 | operator posts: cover, DJ, genres, event, offer + expiry | `updates.py`; `updates.*` | `POST /api/owner/{id}/updates` → `venue_updates` |
| `syn_feedback` | 1,440 | post-visit outcome (visited, rating) | `feedback.py` placeholder chooser over **true** state; `feedback.*` | `POST /api/feedback` → `feedback` |
| `syn_bounties` | 2,409 | bounty board (specs §7.5) | `nightloop.py` (created every 15 min 21:00–02:00 when confidence < 0.30, max 8 open, 60-min expiry, claimed by first verified report) | backend bounty job on real confidence → `bounties` |
| `syn_venue_events` | 65,973 | views / taps / saves / recommendation impressions (owner dashboard demand) | `events.py` fallback: Poisson per venue-slot × busyness, then tap/save funnel; `events.*` | frontend/backend event logging → `venue_events` |
| `syn_disputes` | 250 | owner disputes on reports and their resolution | `trust.py`; `disputes.*` (3% base, ×3 on low-crowd reports, 30% upheld, 48 h auto-reject) | dispute endpoint + moderator script → `disputes` |
| `syn_points_ledger` | 17,702 | points awarded and clawed back (specs §7.2) | `trust.py`; `specs.points_*` | backend points service → `points_ledger` |
| `syn_scout_reputation_history` | 1,644 | reputation/points/level per scout per active night (specs §5.3: join **as of report date**) | `trust.py` time-ordered pass; `specs.rep_*` | nightly snapshot job over real reputation |
| `syn_true_state` | 35,420 | **EVALUATION ONLY**: the unobservable real crowd/dancing/line/cover/genre per 15-min slot | `truth.py`; `truth.*` | none; door counts / verified check-ins as proxies; drop when real |
| `syn_scout_truth` | 209 | **EVALUATION ONLY**: archetype (honest/casual/sloppy/gamer/shill), accuracy, cohort, latent churn date | `scouts.py` + `nightloop.py` (engagement process) | moderation outcomes, real last-active; drop when real |
| `demo_night_snapshots.csv` (committed) | 525 | Live Venue State every 30 min, Sat Nov 14 20:00–03:00 (tableau, v2.2 §J) | `snapshots.py` via `replay.visible` + `recs.live_state` if importable, else `_live_state.py` (specs §5 mirror). `manifest.json` → `snapshot_source` | same query over real reports at those times |
| `extracts/hourly_by_style.csv` | ~120 | hourly report volume / mean crowd by style × weekday × hour (tableau) | `extracts.py` over accepted/disputed reports | same query over real `scout_reports` |

The app and API must never read `syn_true_state` or `syn_scout_truth`; `replay.visible` never returns them.

## Key placeholder numbers (all in `simulator/config/default.json`)
Style peaks dive 00:00, cocktail 22:00, club 01:00, lounge 23:00, pub 22:00, restaurant-bar 21:00; weekday
0.70/0.95/1.00; night/venue-night shocks σ 0.15/0.20; Labor Day Sat ×1.15, Halloween ×1.3; crowd bins
0.2/0.45/0.7/0.9 of capacity; line above 85% occupancy; archetype shares 55/25/10/6/4%; engagement
Beta(2.5, 3.5), weekly decay 0.85, churn below 0.25, 5% returns after ≥ 3 weeks; cover null ~60%, genre null
~40%; 300 users; funnel tap 25% / save 10%. Specs constants (`specs.*`) are copied from specs PRD §5–7 and
CONTRACTS v2 §A, not invented here.

## Manual override
If `data/venue_attributes_manual.csv` exists (same columns as `syn_venue_attributes`, `is_synthetic=0`), its
non-empty values replace the generated attributes before the true state is simulated, so synthetic reports
agree with hand-labelled facts. The simulator never writes that file.
