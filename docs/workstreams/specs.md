# Workstream: specs — as built

Purpose: what the specs workstream built, how to run its checks, results, gaps and assumptions.
Status: done for the Nov 17 demo (MVP slice + extras).
Last updated: 2026-11-17

Owner: Ryan Mehta. Branch: `nightlife/specs`. Plan: `docs/prd/specs/` (PRD, RULES, OUTLINE).

## What was built
| File | What |
|---|---|
| `docs/specs/SCORING.md` | exact formulas: eligibility, decay, weights, field estimates, vibe, confidence + display, trend, match, exclusions, ranking, reason/missing copy, Run My Night, golden format + how to test |
| `docs/specs/PARAMETERS.md` | every constant (table + machine-readable JSON block) |
| `docs/specs/golden_vectors.json` | bundle of G1–G8 (+ parameters, tolerances) for ml-recs/backend tests |
| `docs/specs/golden_synthetic/G1…G8_*.json` | same vectors, one file each (path ml-recs' plan expects) |
| `docs/specs/golden_synthetic/personas_synthetic.json` | 5 synthetic group personas |
| `docs/specs/architecture.md` | diagram, components, `/api/recommend` sequence, data rules, `now=` replay, environments, deploy steps (not deployed), env vars, stack |
| `docs/specs/requirements.md` | US-ON/TP/VC/VP/SC/RW/OW/HM/CP/RL/RN/NF stories with Given/When/Then + traceability table |
| `docs/specs/scout-trust.md` | reputation update, anti-gaming checks by layer, status state machine, disputes, points/levels, bounties |
| `docs/specs/pilot-metrics.md` | metrics, pseudo-SQL, offline protocol (Nov 13–14 holdout), results template |
| `docs/specs/EVALUATION.md` | pointer to pilot-metrics.md (ml-recs plan references this name) |
| `docs/specs/team/` | `PULL_REQUEST_TEMPLATE.md`, `CONTRIBUTING.md`, `GOOD_FIRST_PRS.md` (12 items, placeholder assignees) |
| `docs/specs/tools/` | `reference_scoring.py` (oracle), `build_golden.py`, `check_golden.py`, `check_docs.py`, `test_reference_scoring.py` |
| `docs/synthetic/specs.md` | synthetic registry |

Contract anchors: **G1 vibe 65 / conf 0.67**, **G5 match 83** (rank_score 76.2).

## How to run
```bash
python -I docs/specs/tools/check_golden.py            # golden vectors vs oracle
python -I docs/specs/tools/check_golden.py --regen    # after a PARAMETERS change
python -I -m unittest discover -s docs/specs/tools    # unit tests
python -I docs/specs/tools/check_docs.py              # docs lint
```
Python 3.12+ standard library only.

## Test results (2026-11-17, Python 3.13)
```
$ python -I docs/specs/tools/check_golden.py
check_golden: 8 vectors, 0 errors -> PASS
$ python -I -m unittest discover -s docs/specs/tools
Ran 29 tests in 0.012s
OK
$ python -I docs/specs/tools/check_docs.py
check_docs: 12 docs, 0 errors -> PASS
```

## Notes for consumers
- ml-recs: vibe is computed from **unrounded** crowd/dancing (rounded inputs give 66 for G1);
  match uses the **returned** (rounded) state, as `scoring.recommend(prefs, states, …)` receives it.
  Excluded rows sort after all non-excluded rows (G6: excluded ATT has the higher match but rank 2).
  Field total weight < 0.30 → field null (G2: crowd null though 4 reports are inside the cutoff).
  Operator genres: every listed genre gets the update's full weight.
  No inputs at all → `confidence 0.0`, `display "none"`, vibe/trend/freshness null.
- backend: G1 and G5 inputs are complete in the vector files (reports carry `reputation`).
  Trust rules (rate limits, geofence 150 m, velocity, outlier, owner ban, points, bounties) in scout-trust.md.
- frontend: display bands, vibe labels, stale tag and reason/missing copy in SCORING §5 and §9.

## Assumptions (recorded per build brief)
- File names follow the build brief (`architecture.md`, `requirements.md`, `scout-trust.md`,
  `pilot-metrics.md`) instead of OUTLINE's upper-case names (`ARCHITECTURE.md`, `TRUST.md`,
  `EVALUATION.md`); `EVALUATION.md` kept as a pointer because ml-recs references it.
- `golden_vectors.json` lives at `docs/specs/` (brief's path, outside a `synthetic` folder); it and
  every row carry `is_synthetic: 1` and it is in the registry. Per-vector copies stay in `golden_synthetic/`.
- No Render/Vercel accounts: architecture.md has deploy steps only; nothing deployed.
- Team roster unknown: GOOD_FIRST_PRS assignees are `teammate-1…12`.
- Venue attributes in goldens are synthetic; `data/venue_attributes_manual.csv` overrides when filled.
- No real interviews; persona prefs are synthetic.
- Decisions the PRD left open, now fixed in SCORING.md: weighted median takes the lower value on an
  exact half; `rank_score` is rounded to 1 dp and computed from integer match + 2-dp confidence;
  reasons need component score ≥ 0.6; `prefs.genres` empty scores 1.0 with no reason; live genres
  `[]` count as unknown; `max_*` null → that component's weight is 0 and it never excludes;
  "closed now" uses a venue `is_open_now` boolean that backend/ml-recs derive from OSM hours;
  exclusion check order closed → launch → distance → cover → line.
- Nothing merged to main; no PRs.

## Known gaps
- Mermaid blocks checked for diagram type only; not rendered in GitHub preview yet.
- Golden G9 (line troll) left as good-first-PR #2. No golden for `plan_night` (Later feature).
- `opening_hours` coverage for the 35 launch venues not measured (good-first-PR #3).
- Parameters untuned: tuning needs live-sim training nights and the ml-recs harness.

## Contract change requests
CCR-1…8 from planning are resolved by Contracts v2 (PRD §13). No new requests.
Clarifications (not changes) other teams should adopt: `display` = `none` when confidence < 0.20
**or** vibe null; `confidence` is 0.0 (not null) when a venue has no inputs.
