# RULES for the live-sim build session

Read this file, `docs/CONTRACTS.md` (including the **v2–v2.2 amendments**, which override
the base text), `docs/prd/live-sim/PRD.md`, `docs/prd/live-sim/OUTLINE.md` and
specs' `docs/prd/specs/PRD.md` §5 and §7 (on `nightlife/specs`; built version moves to
`docs/specs/SCORING.md`) before writing any code. If they conflict: CONTRACTS v2 wins,
then specs for scoring/trust constants, then this file, then the PRD.

Deadline: everything pushed by **Fri 2026-11-13 18:00 ET** (CONTRACTS v2 §I).

## 1. Branch and git
- Work only on `nightlife/live-sim` (branched from `nightlife/contracts`).
- Push with `git push -u origin nightlife/live-sim`. No PRs, no pushes to `main`,
  no rebasing other branches.
- Small commits, one task from OUTLINE.md each, message `live-sim: <task>`.
- Never load into or commit `data/manhattan_bars.db`. Synthetic tables go into
  `data/live_sim.db` (or `$LIVE_SIM_DB`), which is never committed (v2 §D).
- Generated CSVs in `data/synthetic_live/` are gitignored; commit only
  `manifest.json`, `validation.json` and `simulator/data/venue_inputs.csv`.

## 2. Stack and versions
- Python 3.13. Use only what `requirements.txt` already has: pandas ≥ 3.0,
  numpy ≥ 2.0, scipy ≥ 1.14 (only if needed), plus the standard library
  (`sqlite3`, `argparse`, `json`, `hashlib`, `zoneinfo`, `datetime`, `pathlib`).
- Dev dependency: pytest ≥ 8, listed in `simulator/requirements-dev.txt`.
- No other new dependencies (no faker, no pyyaml, no SQLAlchemy). Ask in
  `docs/workstreams/live-sim.md` if one seems necessary.
- Run Python with `-I` (`python -I -m simulator ...`), as the rest of the repo does.

## 3. Folders you own (write only here)
- `simulator/` (package, config, tests)
- `data/synthetic_live/` (generated CSVs, manifest, validation report, extracts)
- `data/live_sim.db` (generated output only)
- `docs/synthetic/live-sim.md` (synthetic dataset registry)
- `docs/workstreams/live-sim.md` (what was built, how to run, open issues,
  "Contract change requests")
- `docs/prd/live-sim/` (these planning docs)

## 4. Do not touch
- `docs/CONTRACTS.md`. Put proposed changes in the "Contract change requests"
  section of `docs/workstreams/live-sim.md`.
- `src/`, `run_all.sh`, `reports/`, `data/raw/`, `data/synthetic/` (the existing
  tabular simulators' output), `data/launch_venues.csv`.
- `data/manhattan_bars.db`: read-only, and only by `extract-inputs`. The loader
  must hard-fail on any table name not matching `^syn_[a-z_]+$` and on a target
  path named `manhattan_bars.db`.
- `data/venue_attributes_manual.csv`: read-only input (the team fills it). Generate
  a blank template only inside `data/synthetic_live/`.
- Integration-owned files (v2 §C): `tests/e2e/`, `tests/contract/`, `scripts/`,
  `Makefile`, `.github/`, root `README.md`, `SYNTHETIC_DATA.md`, `DEMO.md`,
  `CONTRIBUTING.md`, `render.yaml`. Root `.gitignore` additions are allowed for
  live-sim outputs only.
- Other workstreams' folders (`recs/`, `backend/`, `frontend/`, `analytics/`,
  `research/`, `coursework/`, `docs/specs/`).
- You may *import* from `src/synth.py` (e.g. for ideas or helpers) but must not edit it.

## 5. Contract fidelity
- Tables have exactly the columns in CONTRACTS.md plus v2 §E additions, in that
  order, with those names (13 tables incl. `syn_venue_events`, `syn_disputes`,
  `syn_points_ledger`, `syn_scout_reputation_history`, `syn_true_state`,
  `syn_scout_truth`) plus `demo_night_snapshots.csv` (v2.2 §J). Write only `syn_` tables;
  backend creates the real twin tables. No extra columns;
  anything else goes in a CCR.
- `syn_true_state` and `syn_scout_truth` are evaluation-only. Nothing in the
  simulator's app-facing tables may be derived from them in a way that leaks truth
  beyond what an observer could see (reports are noisy observations; that is fine).
- Enums exactly as written: style `dive|cocktail|club|lounge|pub|restaurant-bar`;
  crowd 1–5; dancing 0/1/2; report status `pending|accepted|flagged|disputed|removed`
  (store only accepted/flagged/disputed/removed; `pending` is derived at replay);
  event_type `view|tap|save|recommend_impression`; archetype
  `honest|casual|sloppy|gamer|shill`.
- Genres: pipe-separated, only values in `simulator/config/genres.json` (loaded by
  `simulator/config.py` as `GENRES`; there is no `simulator/genres.py`), which must equal the 17-slug list in
  CONTRACTS v2.1 §E exactly. Other workstreams read the JSON;
  never change it without a contract change.
- Specs rules (points, levels, reputation, status, bounties, presence radius 150 m,
  rate limits, half-lives) are read from config keys that cite the specs section.
  Do not invent different values; if specs changes, update config, not logic.
- Models and evaluation join reputation from `syn_scout_reputation_history` as of the
  report date, never the final `syn_scouts.reputation`.
- Churn label is "no report in 21 days" (CONTRACTS v2.1 §B).
- The build command is fixed: `python -I -m simulator --seed 42 --out data/live_sim.db` with optional
  `--nights N`. Don't rename flags; integration and backend call exactly this.
- Never generate or store raw GPS for scouts; only `distance_m`.
- IDs: `syn-r-000123` reports, `syn-s-0042` scouts, `syn-u-` users, `syn-up-` updates,
  `syn-f-` feedback, `syn-b-` bounties, `syn-e-` events, `syn-d-` disputes,
  `syn-p-` ledger, `syn-o-<venue_id>` owners. `venue_id` is the real `license_id`.
- `ts` is ISO 8601 with offset, America/New_York, e.g. `2026-11-14T23:30:00-05:00`.
- `venue_id` is the SLA `license_id` from `data/launch_venues.csv`.
- Nullable fields are empty in CSV and `NULL` in SQLite. Never fill a missing
  value with a favourable default.
- `prefs_json` is a JSON object that matches the Preferences block in CONTRACTS.md.

## 6. Synthetic-data marking (mandatory)
1. Every row of every output table has `is_synthetic = 1`.
2. All output files live under `data/synthetic_live/`. All DB tables start with `syn_`.
3. Every place that invents a number, rule or distribution carries a comment
   `# SYNTHETIC: <real source that replaces this>`. Example:
   `# SYNTHETIC: replace with hourly occupancy from real Scout reports (Spring 2027 pilot)`.
   This applies to config keys too: each key in `default.json` has a sibling
   `"_note"` string giving the same information.
4. `docs/synthetic/live-sim.md` lists every dataset with: file/table, what it
   imitates, how generated (module + config keys), the real source that replaces
   it, and swap steps. Update it in the same commit as any new dataset.
5. Synthetic IDs start with `syn-`.
6. `validate` fails if any row has `is_synthetic != 1` or any file is written
   outside `data/synthetic_live/` (or the `--out` folder, which must contain
   `synthetic` in its path), except the DB file `data/live_sim.db` / `$LIVE_SIM_DB`
   named by CONTRACTS v2 §D.

## 7. Coding conventions
- Package layout as in OUTLINE.md. One stage per module, each a pure function
  `fn(cfg, rng, inputs...) -> pd.DataFrame`. No module-level state.
- Randomness: a single master seed. Each stage gets its own
  `np.random.Generator` from `np.random.SeedSequence(seed).spawn(...)` keyed by a
  stable stage name (use `hashlib.sha256`, never Python's `hash()`), so editing one
  stage does not change another stage's output. Never call `np.random.*` globals or
  `random`.
- All tunable numbers in `simulator/config/default.json`. Logic modules contain no
  magic numbers except unit conversions.
- Work in UTC internally (`pandas.Timestamp`, tz-aware); convert to
  America/New_York only when writing.
- Sort rows deterministically before writing (by `ts`, then ID). CSV written with
  `index=False`, `lineterminator="\n"`, fixed float format (`%.3f`).
- Type hints on public functions, a short docstring on every module. Keep
  functions under ~60 lines.
- Format with `ruff format` if available; otherwise follow PEP 8. No notebooks in
  `simulator/`.
- Logging via `logging`, not `print`, except CLI output.

## 8. Testing requirements
- `python -I -m pytest simulator/tests -q` must pass before every push.
- Required tests (see OUTLINE.md test plan for detail):
  - schema: each contract table has exactly the contract columns and valid types,
    ranges, enums and nulls;
  - referential integrity (venue_id, scout_id, user_id exist);
  - determinism: two runs with the same seed give identical file hashes; a
    different seed gives different hashes;
  - stage isolation: changing a users-stage config key leaves report hashes unchanged;
  - DST: the Oct 31 night produces monotonic UTC times and valid local offsets;
  - loader safety: loading never alters a non-`syn_` table (checksum before/after
    on a temp copy of the DB), and refuses bad table names;
  - replay: `visible(now)` never returns a row with `ts > now`, expired offers or
    claimed bounties;
  - specs rules: golden vector G1 for the confidence mirror; reputation, points,
    level, velocity/outlier flags and bounty rules on hand-made cases;
  - scouts: no reports after `churned_at` (except configured returns);
  - realism checks in `validate` run on the small preset in CI-sized time.
- Tests use a temp directory and a tiny config; they must not write into
  `data/synthetic_live/`.
- Full test suite runs in under 60 s.

## 9. Definition of done
- [ ] `python -I -m simulator --seed 42 --out data/live_sim.db` (seed 42) produces all 13 tables in
      `data/synthetic_live/`, passes `validate`, and loads `data/live_sim.db`;
      row counts match; works without `data/manhattan_bars.db` present.
- [ ] `simulator/config/genres.json` pushed early (research and others use it).
- [ ] `demo_night_snapshots.csv` (525 rows) committed; `snapshot_source` in manifest.
- [ ] `python -I -m simulator replay --now 2026-11-14T23:30:00-05:00` prints the
      DEMO_NOW snapshot; `--shift-to 2026-11-17` works.
- [ ] pytest suite green.
- [ ] `docs/synthetic/live-sim.md` registry complete; `docs/workstreams/live-sim.md`
      says what was built, how to run it, known limits, open issues, contract change
      requests.
- [ ] 36 nights (Thu 2026-08-27 → Sat 2026-11-14, 20:00–03:00 ET); CSVs ≤ 30 MB; full build < 60 s on a laptop CPU;
      `--nights 3` works.
- [ ] `grep -rn "SYNTHETIC:" simulator/` covers every module that invents data.
- [ ] Branch pushed by Fri Nov 13 18:00 ET; master session told the manifest hashes.
