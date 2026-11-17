# Good first PRs

Purpose: one small, reviewable PR per team member (course requirement: everyone lands a merged PR).
Status: draft — roster unknown; assignees are placeholders (`teammate-1` …) until handles are known.
Last updated: 2026-11-17

Each item is ≤ 1 h, touches one owned folder, and has a test or visible output.
Branch: `fp/<handle>-<topic>`. Use `docs/specs/team/PULL_REQUEST_TEMPLATE.md`.

| # | Assignee | Area (folder) | Task | Done when |
|---|---|---|---|---|
| 1 | teammate-1 | integration (`.github/`, root) | Copy `docs/specs/team/PULL_REQUEST_TEMPLATE.md` → `.github/pull_request_template.md` and `CONTRIBUTING.md` → root | template appears on a new PR |
| 2 | teammate-2 | specs (`docs/specs/`) | Add golden vector G9 "line troll": one report says 60 min line; weighted median stays 10 | `check_golden.py` passes with 9 vectors |
| 3 | teammate-3 | specs (`docs/workstreams/specs.md`) | Report OSM `opening_hours` coverage for the 35 launch venues (read-only DB query) | table with count + share |
| 4 | teammate-4 | frontend (`frontend/`) | "demo data" badge component + story/test | badge renders when `is_synthetic` |
| 5 | teammate-5 | frontend (`frontend/`) | Confidence display component: show / low / none bands + stale tag (SCORING §5) | unit test for 0.39 / 0.40 / 0.19, freshness 61 |
| 6 | teammate-6 | backend (`backend/`) | `/api/health` shape `{ok, recs, data, demo_now}` + pytest | test green |
| 7 | teammate-7 | backend (`backend/`) | 429 rate-limit message copy (scout-trust §2) + test | test green |
| 8 | teammate-8 | ml-recs (`recs/`) | haversine util + tests using two launch venues | test green |
| 9 | teammate-9 | tableau (`analytics/tableau/`) | Launch-venues extract with 311 count labelled "311 noise-complaint risk" | CSV + caption |
| 10 | teammate-10 | research (`research/`) | Add 2 competitor rows to the competitive matrix | rows with sources |
| 11 | teammate-11 | integration (root `README.md`) | "Nightlife Autopilot" section linking `docs/specs/` | links resolve |
| 12 | teammate-12 | ml-recs (`recs/tests/`) | Load `docs/specs/golden_vectors.json` in a parametrised pytest | G1–G8 run in CI |

If the team has fewer people, drop from the bottom; if more, split #4/#5 or add more golden vectors (G10: missing dancing with `want_dancing=false`).
