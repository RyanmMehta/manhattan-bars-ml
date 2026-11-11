# RULES for the live-sim build session

Read this file, `docs/CONTRACTS.md`, `docs/prd/live-sim/PRD.md` and
`docs/prd/live-sim/OUTLINE.md` before writing any code. If they conflict,
CONTRACTS.md wins, then this file, then the PRD.

## 1. Branch and git
- Work only on `nightlife/live-sim` (branched from `nightlife/contracts`).
- Push with `git push -u origin nightlife/live-sim`. No PRs, no pushes to `main`,
  no rebasing other branches.
- Small commits, one task from OUTLINE.md each, message `live-sim: <task>`.
- Never commit `data/manhattan_bars.db` after loading `syn_` tables into it. Run
  `git checkout data/manhattan_bars.db` (or load into a separate DB) before
  committing.

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
- `data/synthetic_live/` (generated CSVs, manifest, validation report)
- `docs/synthetic/live-sim.md` (synthetic dataset registry)
- `docs/workstreams/live-sim.md` (what was built, how to run, open issues,
  "Contract change requests")
- `docs/prd/live-sim/` (these planning docs)

## 4. Do not touch
- `docs/CONTRACTS.md`. Put proposed changes in the "Contract change requests"
  section of `docs/workstreams/live-sim.md`.
- `src/`, `run_all.sh`, `reports/`, `data/raw/`, `data/synthetic/` (the existing
  tabular simulators' output), `data/launch_venues.csv`.
- Non-`syn_` tables in `data/manhattan_bars.db`. The loader must hard-fail on
  any table name not matching `^syn_[a-z_]+$`.
- Other workstreams' folders (`recs/`, `backend/`, `frontend/`, `analytics/`,
  `research/`, `coursework/`, `docs/specs/`).
- You may *import* from `src/synth.py` (e.g. for ideas or helpers) but must not edit it.

## 5. Contract fidelity
- Contract tables have exactly the columns in CONTRACTS.md, in that order, with
  those names. Extra columns go in separate truth tables, never in contract tables.
- Enums exactly as written: style `dive|cocktail|club|lounge|pub|restaurant-bar`;
  crowd 1–5; dancing 0/1/2; genres pipe-separated lowercase.
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
   `synthetic` in its path).

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
  - realism checks in `validate` run on a small config (2 nights) in CI-sized time.
- Tests use a temp directory and a tiny config; they must not write into
  `data/synthetic_live/`.
- Full test suite runs in under 60 s.

## 9. Definition of done
- [ ] `python -I -m simulator generate --seed 42` produces all tables in
      `data/synthetic_live/` with `manifest.json`.
- [ ] `python -I -m simulator validate` passes every check and writes `validation.json`.
- [ ] `python -I -m simulator load --db <path>` loads all `syn_` tables; row counts match.
- [ ] `python -I -m simulator replay --preset demo` prints the demo-night snapshot;
      `--shift-to` works.
- [ ] pytest suite green.
- [ ] `docs/synthetic/live-sim.md` registry complete; `docs/workstreams/live-sim.md`
      says what was built, how to run it, known limits, open issues, contract change
      requests.
- [ ] Output ≤ 20 MB; generation ≤ 60 s.
- [ ] `grep -rn "SYNTHETIC:" simulator/` covers every module that invents data.
- [ ] Branch pushed; master session told the pinned seed and demo time.
