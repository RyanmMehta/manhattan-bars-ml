# Brief: backend

You are one sub-session ("subtab") of the Party Engine / Nightlife Autopilot class project (owner: Ryan Mehta). A master session coordinates you. PLANNING ONLY in this phase: write documents, do NOT write application code, scripts, or data files yet. Work autonomously without asking questions; record assumptions.

First read docs/CONTRACTS.md, README.md, src/*.py (skim) and data/launch_venues.csv. Follow CONTRACTS.md (folder ownership, schemas, API, synthetic-data rule). Create branch `nightlife/backend` from `nightlife/contracts`, commit, and push with `git push -u origin nightlife/backend`. No PRs, no pushes to main, don't edit CONTRACTS.md (put proposed changes in a "Contract change requests" section).

Project context: Nightlife Autopilot helps groups choose where to go right now by matching their preferences with fresh info about nearby venues; launch = 35 LES venues (zip 10002). Users: consumers/groups, Scouts (10-second vibe check: crowd, dancing, line, optional cover/music; points, reputation, leaderboard, bounties), venue operators (claimed profile, updates, offers, demand analytics). Three scores: vibe (0-100 current energy), match (fit to group), confidence (support from fresh credible reports). MVP: venue profiles, filters, search, Scout mode + rewards/leaderboard, owner dashboard. Later: availability heatmap, compatibility score, recommendation list, Run My Night routing. Already built: public-data pipeline (SLA licenses, DOHMH inspections, 311 noise, OSM) → data/manhattan_bars.db (5,737 venues, v_bars 1,727), CART/copula/independent synthetic generators, complaint-risk models (ROC AUC ~0.72; complaint risk ≠ nightlife quality). No live data, users, backend, frontend, or deployment exists yet. Course deadlines: Nov 10 frontend mockups; Nov 17 integration = working model, deployed. Anything without real data will be synthetic, clearly marked, and swappable later.

Write these files in docs/prd/backend/:
1. PRD.md — problem, goals/non-goals, users, user stories with acceptance criteria, scope (MVP vs later), requirements, dependencies on other workstreams (by name: specs, research, tableau, live-sim, ml-recs, backend, frontend, coursework, integration), success metrics, risks, open questions.
2. RULES.md — CLAUDE.md-style rules the future build session must follow: stack/versions, folder it owns, coding conventions, testing requirements, synthetic-data marking (is_synthetic, syn_ prefix, `# SYNTHETIC:` comments, registry in docs/synthetic/backend.md), what it must not touch, definition of done.
3. OUTLINE.md — the build plan: ordered tasks with checkboxes and size estimates, file tree to be created, interfaces consumed/provided (referencing CONTRACTS.md), synthetic datasets it will need (each: what it imitates, how to generate, real source that replaces it, swap steps), test plan, demo script.
Keep each doc concrete and implementable; cite numbers as placeholders when unknown.

When done, push, and if you have a send_message tool, send master session session_011S9YErq8N439fyeHyMMDMr a 5-line summary (branch, files, top open questions). Then stop and wait for the instruction to build.

Your workstream: NAME = backend.

Scope: FastAPI service in backend/ implementing every endpoint in CONTRACTS.md, DB schema/migrations (SQLite now, Postgres-ready via SQLAlchemy), loading venue data + syn_ tables, importing recs/ with a stub fallback, auth approach for scouts/owners (simple for MVP), CORS, tests (pytest), Dockerfile, render.yaml, env vars, and deploy steps (Ryan must supply accounts). Covers Oct 13 'deployed team skeleton'.
