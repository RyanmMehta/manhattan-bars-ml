# RULES for the tableau build session

Read this before writing any code. It works like a CLAUDE.md for this workstream.
Contracts in `docs/CONTRACTS.md` win if anything here conflicts.

## Stack and versions
- Python 3.11+ (match the existing pipeline). Use the root `requirements.txt`
  (pandas ≥ 3.0, numpy ≥ 2.0) plus `matplotlib>=3.9` only, declared in
  `analytics/tableau/requirements.txt`. No seaborn, plotly, geopandas or basemap
  downloads (no network at render time).
- Standard library `sqlite3` for DB access, opened read-only:
  `sqlite3.connect("file:data/manhattan_bars.db?mode=ro", uri=True)`.
- Tableau Public (Desktop, current free version, e.g. 2025.x) for the workbook.
  Save as `.twbx` (packaged, so extracts travel with it).
- Tests: `pytest>=8`. Run scripts with `python -I`.

## Folder ownership
- You own `analytics/tableau/` (everything inside), `docs/synthetic/tableau.md`
  and `docs/workstreams/tableau.md`. Planning docs live in `docs/prd/tableau/`.
- Read-only for you: `data/manhattan_bars.db`, `data/launch_venues.csv` (header
  `license_id`, alias `AS venue_id`), `data/live_sim.db` (live-sim; path from env
  `LIVE_SIM_DB`; generated, never committed), `recs/` (ml-recs, import only).
- Never read the evaluation-only tables `syn_true_state` and `syn_scout_truth`.
- Contract: CONTRACTS.md v2.2 (commit 2cdf1f0). Heatmap cell HH = HH:30 row of `data/synthetic_live/demo_night_snapshots.csv` (read-only, live-sim owned). Join reputation as of the report date (`syn_scout_reputation_history`), never final reputation. Use its constants (§A) and DEMO_NOW
  `2026-11-14T23:30:00-05:00` (§B); never invent different ones.

## Must not touch
- `src/`, `data/manhattan_bars.db`, `data/live_sim.db`, `data/raw/`, `data/synthetic/`, `reports/`, `run_all.sh`, root `requirements.txt`.
- Integration-owned files (`tests/e2e/`, `tests/contract/`, `scripts/`, `Makefile`, `.github/`, root `README.md`, `SYNTHETIC_DATA.md`, `DEMO.md`).
- Any other workstream's folder (`simulator/`, `recs/`, `backend/`, `frontend/`, `research/`, `coursework/`, `docs/specs/`).
- `docs/CONTRACTS.md` — put proposals in "Contract change requests" in `docs/workstreams/tableau.md`.
- `main` branch. Work on `nightlife/tableau`, push with `git push -u origin nightlife/tableau`, no PRs.

## Coding conventions
- Two scripts, each runnable alone with `--db`, `--out` and `--synthetic-dir` flags and sensible defaults:
  `export_extracts.py` (DB → CSVs) and `render_standin.py` (CSVs → PNG).
- SQL lives in `analytics/tableau/queries.py` as named constants, one per extract.
- Colours, bucket edges and labels live once in `analytics/tableau/style.py`;
  BUILD_TABLEAU.md copies the same hex codes.
- Synthetic ids start with `syn-` (placeholder: `syn-r-T1-…`, `syn-s-T1-…`).
- Deterministic output: `ORDER BY venue_id` (or the natural key), floats rounded
  to 5 dp for coordinates and 2 dp for scores, `lineterminator="\n"`, fixed RNG seed (42).
- Column names: snake_case, `venue_id` (never `license_id`) in outputs.
- Missing values stay empty in CSV (`NULL` in Tableau). Never fill with a favourable default.
- Functions small with docstrings; no notebooks committed as the source of truth.
- Paths built from the repo root (`Path(__file__).resolve().parents[2]`), never hard-coded absolute paths.

## Synthetic-data marking (mandatory)
1. Every extract has `is_synthetic` (0 public, 1 synthetic). Mixed files are not allowed:
   synthetic rows go in their own file.
2. Synthetic extracts go in `analytics/tableau/extracts/synthetic/` and their names start with `syn_`.
3. Every code line that reads or creates synthetic data has
   `# SYNTHETIC: <real source that replaces this>` above it.
4. Every synthetic dataset is listed in `docs/synthetic/tableau.md` with: file,
   what it imitates, how it was generated (command + seed), real replacement, swap steps.
5. Every Tableau sheet and PNG panel showing synthetic data carries a visible
   "DEMO DATA (synthetic)" label in its title, plus the badge colour from `style.py`.
6. Complaint-based sheets carry the caption "311 noise complaints = complaint risk, not nightlife quality."

## Testing requirements
- `pytest analytics/tableau/tests` must pass before every push.
- Required tests:
  - each extract exists, has the expected columns in order, and has `is_synthetic`;
  - row counts: bars 1,727; launch 35; neighbourhood rows = distinct neighbourhoods in `venues`;
  - all `venue_id` in launch extract are in bars extract;
  - every file under `extracts/synthetic/` has `is_synthetic == 1` on all rows and a `syn_` name;
  - no public extract has `is_synthetic == 1`;
  - the tonight extract validates against the contract `syn_scout_reports` field ranges
    (crowd 1-5, dancing 0-2, line_minutes ≥ 0) and vibe_score in 0-100;
  - running the exporter twice yields identical file hashes;
  - `render_standin.py` writes a PNG ≥ 2400×1600 px (use `--out` to a tmp dir).
- Tests use the real DB read-only; skip with a clear message if the DB is absent.

## Definition of done
- [ ] Extracts + PNG regenerate from a clean checkout with two commands.
- [ ] All tests pass.
- [ ] Workbook `.twbx` committed; dashboard published on Tableau Public; link recorded.
- [ ] `BUILD_TABLEAU.md` followed end-to-end once by someone other than the author (or a fresh session).
- [ ] `docs/synthetic/tableau.md` lists every synthetic file; `grep -rn "SYNTHETIC:" analytics/tableau` matches each one.
- [ ] `docs/workstreams/tableau.md` says what was built, how to run it, known issues, contract change requests.
- [ ] Branch `nightlife/tableau` pushed by **Fri Nov 13 18:00 ET**; no files outside owned folders changed (`git diff --stat origin/nightlife/contracts`).
- [ ] Heatmap shows the v2 display threshold and the DEMO_NOW 23:30 line; fallback scorer (if used) passes golden vector G1.
