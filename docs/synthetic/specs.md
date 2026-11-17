# Synthetic data registry — specs

Purpose: every synthetic/placeholder dataset the specs workstream created (Contracts synthetic-data rule 4).
Status: agreed.
Last updated: 2026-11-17

| File / table | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `docs/specs/golden_synthetic/G1_normal_four_scouts.json` … `G9_energy_contradiction.json` (files: G1_normal_four_scouts.json, G2_stale_reports.json, G3_single_scout.json, G4_operator_only.json, G5_match_contract_prefs.json, G6_exclusion_known_vs_unknown.json, G7_disputed_and_flagged.json, G8_trend_rising_falling.json, G9_energy_contradiction.json) | small slices of a night's scout reports, operator updates, scouts and venue attributes at real launch venues | inputs hand-written in `docs/specs/tools/build_golden.py`; `expected` computed by `reference_scoring.py`; G1 and G5 hand-checked (PRD §5.8, §5.10) | **not replaced** — test fixtures. Optionally add a vector from a real anonymised pilot night | keep; after a parameter change run `python -I docs/specs/tools/check_golden.py --regen`, review diff, commit, tell ml-recs/backend |
| `docs/specs/golden_vectors.json` | bundle of the same G1–G9 vectors + parameters + tolerances | written by `build_golden.py` | not replaced (test fixture) | regenerated with the files above. Lives outside a `synthetic` path because the build brief fixed this path; file and every row carry `is_synthetic: 1` |
| `docs/specs/golden_synthetic/personas_synthetic.json` | 5 group personas' Preferences (dancer group, cocktail pair, budget crew, group of 8, no prefs) | hand-written from PRD §3, lat/lon near Delancey/Essex | research interview results | replace values, keep ids, set `is_synthetic: 0`, update this row |
| Venue `capacity`/`genres` inside golden vectors | `syn_venue_attributes` | hand-written | `data/venue_attributes_manual.csv` | update `VENUES` in `build_golden.py`, regen |
| Parameter values in `docs/specs/PARAMETERS.md` | tuned constants | first guesses (PRD §5, §7) | tuning on live-sim training nights, then pilot data | edit table + JSON block, regen goldens, notify master |
| Targets in `docs/specs/pilot-metrics.md` §1 | pilot goals | first guesses | real pilot baseline / course feedback | edit table |
