# RULES — frontend build session

Read this before writing any code in `frontend/`. It's the CLAUDE.md for this workstream.
The source of truth for data shapes and the API is `docs/CONTRACTS.md`. Requirements are in
`docs/prd/frontend/PRD.md` and the task order is in `docs/prd/frontend/OUTLINE.md`.

## 1. Scope and ownership
- You own **`frontend/`** only, plus `docs/workstreams/frontend.md` and
  `docs/synthetic/frontend.md`.
- Do **not** edit: `src/`, `data/` (the DB or CSVs), `backend/`, `recs/`, `simulator/`,
  `research/`, `analytics/`, `coursework/`, `docs/specs/`, `docs/CONTRACTS.md`, or any
  other workstream's docs.
- You may **read** `data/launch_venues.csv` and `data/synthetic_live/*.csv`. A script under
  `frontend/scripts/` may copy them into `frontend/src/mocks/fixtures/`. The originals stay
  untouched.
- Contract changes go under "Contract change requests" in `docs/workstreams/frontend.md`
  (and PRD §12). Never change the contract on this branch.
- Git: work on `nightlife/frontend`. Push with `git push -u origin nightlife/frontend`.
  No PRs and no pushes to `main`.

## 2. Stack (pin exact versions in package.json, no `^`)
| Concern | Choice |
|---|---|
| Runtime | Node 20 LTS (`.nvmrc` = `20`), npm (commit `package-lock.json`) |
| Build | Vite 5.x + `@vitejs/plugin-react` |
| Language | TypeScript 5.x with `strict: true`, `noUncheckedIndexedAccess: true` |
| UI | React 18.3.x, React Router 6.x (data routers not required) |
| Server state | TanStack Query 5.x: all API reads go through it |
| Client state | React context + `useReducer` for prefs/persona/`now`. No Redux. |
| Styling | Tailwind CSS 3.4.x with design tokens in `tailwind.config.ts` + CSS vars in `src/styles/tokens.css` |
| Map | `maplibre-gl` 4.x, lazy-loaded; key-free dark style |
| Charts | Recharts 2.x (owner dashboard only, lazy-loaded) |
| Mock API | MSW 2.x |
| Unit/component tests | Vitest 2.x + @testing-library/react + jsdom |
| E2E + mockups | Playwright (use the preinstalled one: `require('playwright')`, or `@playwright/test` with `executablePath: '/opt/pw-browsers/chromium'` if versions differ). Always run with `--trace off`. |
| Lint/format | ESLint 9 (typescript-eslint, react-hooks, jsx-a11y) + Prettier 3 |
| Deploy | Vercel (static SPA build, `vercel.json` rewrites to `index.html`) |

Don't add a dependency outside this table without writing the reason in
`docs/workstreams/frontend.md`.

## 3. Coding conventions
- File names: components `PascalCase.tsx`, hooks `useThing.ts`, everything else `camelCase.ts`.
- One component per file. Named exports only, no default exports (except route lazy chunks).
- **Types mirror CONTRACTS.md field names exactly** (snake_case on the wire, e.g. `vibe_score`).
  Don't rename them to camelCase in API types. Derived view models may use camelCase and live
  in `src/api/adapters.ts`.
- All fetches go through `src/api/client.ts`. No `fetch` calls in components. Every GET
  appends `now` when the demo clock is set.
- Thresholds and magic numbers live only in `src/config/thresholds.ts`. Values from
  CONTRACTS §A (`CONF_SHOW = 0.40`, `CONF_LOW = 0.20`, `PRESENCE_RADIUS_M = 150`) cite
  §A in a comment. Frontend-only placeholders (vibe label bands, `STALE_MIN = 90`,
  refresh interval) carry `// TODO(specs):`. Prefer `state.display` over computing
  the band when the backend sends it.
- **Null means unknown.** Render `null` as "not reported" via `<Unknown/>`. Never `?? 0` or
  `|| default` on a Live Venue State field. ESLint rule or test enforces this for
  `src/components/venue/*`.
- No scoring, ranking, or routing logic in the frontend. Client-side sort on returned fields
  is the only exception.
- `complaint_risk` shows only on the profile, labelled "311 noise-complaint risk". It
  never appears in vibe, match, or sorting UI. List order comes from the backend's `rank`.
- Styling: Tailwind utilities with tokens. No hex literals outside `tokens.css` /
  `tailwind.config.ts`. Dark only.
- Accessibility: every interactive element has an accessible name. Vibe colour always comes
  with a number or label. Tap targets ≥ 44 px. Respect `prefers-reduced-motion`.
- Every screen has loading, empty, and error states.
- No `any`. Use `unknown` plus narrowing for external data. Validate API responses with
  hand-written type guards in `adapters.ts` (zod is allowed if it's added to the table).
- Env vars: only the names reserved in CONTRACTS §H: `VITE_API_MODE` (`mock`|`live`),
  `VITE_API_BASE`, `VITE_DEMO_NOW`, `VITE_FEATURE_ROUTING`, and `VITE_FEATURE_HEATMAP`.
  They're documented in `frontend/.env.example`. No secrets in the frontend.
- Auth: the demo-login bearer token lives in `sessionStorage` (`na.token.v1`). It's
  attached only by `client.ts` and only to `/api` writes. On 401, re-login silently.
- Errors: parse `{"error": {code, message, details}}`. Never show raw stack traces.
- Genres: use only the shared vocabulary in CONTRACTS §E (`src/config/genres.ts`,
  copied from `simulator/genres.py` when it exists).

## 4. Synthetic data marking (mandatory, CONTRACTS.md rule)
1. Every fixture row keeps `is_synthetic: 1`. Fixtures live under
   `frontend/src/mocks/fixtures/synthetic/` (the path contains `synthetic`).
   Fixture files created by this workstream start with `syn_` (e.g.
   `syn_recommendations.json`), and synthetic IDs start with `syn-` (CONTRACTS §D).
2. Every code spot that uses synthetic data or a placeholder gets
   `// SYNTHETIC: <real source that replaces this>`, e.g.
   `// SYNTHETIC: replace with GET /api/owner/{id}/dashboard from backend analytics`.
3. `<DemoBadge/>` renders wherever displayed data has `is_synthetic` truthy, and as a
   persistent banner in mock mode or when `X-Data`/`health.data` is `synthetic|mixed`. A test walks every route in mock mode and asserts that a
   badge or banner is visible.
4. Every synthetic dataset is registered in **`docs/synthetic/frontend.md`** with: file/table,
   what it imitates, how it was generated, the real source that should replace it, and the
   swap steps. Add the entry in the same commit that adds the data.
5. Placeholder UI copy (fake points, fake owner KPIs) also counts as synthetic: mark it and
   register it.

## 5. Testing requirements
- `npm run typecheck`, `npm run lint`, `npm test` (Vitest), and `npm run e2e` (Playwright,
  mock mode) must all pass before every push.
- Unit tests: `client.ts` (query building, `now` param, error mapping), `adapters.ts`
  (null handling, name cleaner), `thresholds` usage, and the prefs reducer and its
  localStorage persistence.
- Component tests: `VenueCard`, `PickHero`, `ConfidenceMeter`, `VibeBadge`, `DemoBadge`,
  `VibeCheckForm`, `FilterBar`. Each covers null fields, low-confidence, stale, and
  synthetic cases.
- E2E (Playwright, mock mode, 390×844): onboarding → pick → profile → directions; browse +
  filter + search; vibe check submit < 10 s of scripted interaction; leaderboard; owner
  update; demo time travel; synthetic badge on every route.
- Contract test: the TS types are checked against a sample JSON per endpoint in
  `src/mocks/fixtures/contract-samples/`, copied from CONTRACTS.md examples. When the
  backend is live, `npm run contract:live` hits `/api/*` and validates the shapes.
- Coverage target: ≥ **70%** lines on `src/api`, `src/state`, `src/components`.
- Lighthouse (mobile) on the production build: Perf ≥ 85, A11y ≥ 95. Record the scores in
  `docs/workstreams/frontend.md`.

## 6. Commits
- Small commits, imperative subject, one task ID from OUTLINE.md in the subject
  (e.g. `T7: vibe check form`).
- Never commit `.env`, `node_modules/`, `dist/`, Playwright traces, or any secret.
- Frontend tests stay in `frontend/tests/`. Root `tests/e2e/` and `tests/contract/`
  belong to integration (CONTRACTS §C).
- Mockup PNGs are committed (they're a course deliverable). Keep each under 1.5 MB.

## 7. Definition of done (per task, and for the workstream)
A task is done when:
- [ ] Its acceptance criteria in PRD §4 pass, with a test referencing the US-ID.
- [ ] Typecheck, lint, unit, and e2e pass locally.
- [ ] It works in both `mock` and `live` modes (live may be verified against a local backend
      or marked "pending backend").
- [ ] Loading, empty, and error states exist and synthetic data is badged and registered.
- [ ] OUTLINE.md checkbox ticked and `docs/workstreams/frontend.md` updated.

The workstream is done (Nov 17) when:
- [ ] Every MVP screen in PRD §5 is reachable on the Vercel URL.
- [ ] Mockup PNGs plus contact sheet are in `frontend/mockups/`.
- [ ] `docs/workstreams/frontend.md` covers what was built, how to run it, env vars, deploy
      URL, Lighthouse scores, open issues, and contract change requests.
- [ ] `docs/synthetic/frontend.md` lists every synthetic dataset and placeholder.
- [ ] The demo script (OUTLINE §7) runs end to end with no console errors.
