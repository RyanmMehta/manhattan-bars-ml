# OUTLINE — frontend build plan

Follow `RULES.md`. The user stories (US-xx) are in `PRD.md` §4.
Sizes: **S** ≤ 1 h · **M** 1–3 h · **L** 3–6 h (one build session).
Target order: mock-mode screens first, then the live API, then deploy. Mockup PNGs are
the **first priority, due Thu Nov 12** (master, CONTRACTS §I). Upstream lands Fri Nov 13
18:00; integration merges frontend last; freeze Nov 16 20:00.

**Mockup fast path (Nov 11–12):** T1 → T2 → T3 → T4 (types only) → T5 (seeded fixtures
only) → T6–T14 at mock-mode quality (map dots without heat; owner chart static) → T15
export. Everything else is polish after the PNGs are sent.

## 1. Ordered tasks

### Phase A: skeleton and design system (Nov 11)
- [ ] **T1** (M) Scaffold `frontend/`: Vite React-TS, pinned deps, `.nvmrc`, Tailwind,
      ESLint/Prettier, Vitest, Playwright config, `.env.example`, `npm` scripts
      (`dev`, `build`, `preview`, `typecheck`, `lint`, `test`, `e2e`, `mockups`,
      `contract:live`, `fixtures`).
- [ ] **T2** (M) Design tokens (`tokens.css`, `tailwind.config.ts`) and primitives:
      `Button`, `Chip`, `Card`, `Sheet`, `Slider`, `Toggle`, `Skeleton`, `Toast`,
      `EmptyState`, `ErrorState`, `Unknown`, `DemoBadge`, `DemoBanner`.
- [ ] **T3** (M) Domain components: `VibeBadge`, `ConfidenceMeter`, `FreshnessTag`,
      `TrendArrow`, `ReasonList`, `MissingList`, `VenueCard`, `VenueCardCompact`,
      `PickHero`, `ScoreTriplet` (vibe / match / confidence) + component tests.
- [ ] **T4** (M) API layer: `types.ts` (CONTRACTS §F/§G shapes), `client.ts` (`now`
      param, bearer token, error envelope, `X-Total-Count`/`X-Data` headers),
      `adapters.ts` (display band, name fallback, null guards), `queries.ts`
      (TanStack hooks), `auth.ts` (demo-login). Unit tests.
- [ ] **T5** (L) Mock API: MSW handlers for all 14 endpoints (CONTRACTS table + §G
      `auth/demo-login`, `feedback`), plus
      `scripts/build-fixtures.mjs`, which builds `syn_*` fixtures from
      `data/launch_venues.csv` and `data/synthetic_live/*.csv` if present, or else from a
      seeded generator (§5). Register in `docs/synthetic/frontend.md`.

### Phase B: screens in mock mode (Nov 11–12) → mockups by Thu Nov 12
- [ ] **T6** (S) App shell: router (PRD F7), bottom tab bar (Pick / Browse / Map / Scout /
      More), header with Prefs chip, persona context with demo-login, demo panel (US-10),
      `config/thresholds.ts`, `config/genres.ts`.
- [ ] **T7** (M) Onboarding / prefs screen + `prefsReducer` + localStorage (US-01).
- [ ] **T8** (M) Tonight pick screen (US-02).
- [ ] **T9** (M) Browse: filter bar, search, sort, card list (US-03).
- [ ] **T10** (M) Venue profile (US-04).
- [ ] **T11** (L) Map + heat layer + time slider, lazy chunk, SVG fallback (US-05).
- [ ] **T12** (M) Scout vibe check with nearest-venue pick, a "within 150 m" hint
      (the server decides `verified_presence`), and offline queue (US-06).
- [ ] **T13** (S) Leaderboard + bounties (US-07).
- [ ] **T14** (M) Owner dashboard: KPI tiles, demand chart, update form and preview (US-09).
- [ ] **T15** (M) Mockup export: `scripts/mockups.mjs` (Playwright, mock mode, fixed
      `now=2026-11-14T23:30:00-05:00`), 390×844 @2x for every route plus 1440×900 for
      owner and map, then a contact sheet. Write `frontend/mockups/README.md`.
      **Send the PNGs to the master session as soon as they exist (late Nov 10
      deliverable).**

### Phase C: live API, stretch, deploy (Nov 14–16)
- [ ] **T16** (M) Live mode against a local backend (`uvicorn` on :8000 via Vite proxy):
      fix adapter mismatches, run `contract:live`, and log diffs as CRs.
- [ ] **T17** (M) Run My Night timeline, swap stop (`exclude_venue_ids`), and route
      mini-map behind `VITE_FEATURE_ROUTING` (US-08). Stretch.
- [ ] **T18** (S) Post-visit feedback prompt → `POST /api/feedback`. Stretch.
- [ ] **T19** (M) E2E suite (RULES §5) + synthetic-badge route walk + a11y checks
      (axe via Playwright).
- [ ] **T20** (S) Perf pass: lazy chunks, bundle check (≤ 250 KB gzip initial),
      Lighthouse. Record the scores.
- [ ] **T21** (S) Vercel deploy: `vercel.json` (SPA rewrite, optional `/api/*` rewrite to
      Render), env vars per environment, and a preview URL. Ryan supplies the account.
- [ ] **T22** (S) Docs: `docs/workstreams/frontend.md`, final `docs/synthetic/frontend.md`,
      README section in `frontend/README.md`.

Total ≈ 14 M + 3 L + 6 S ≈ **40–55 h**.

## 2. File tree to be created
```
frontend/
  .nvmrc  .env.example  index.html  package.json  package-lock.json
  tsconfig.json  vite.config.ts  tailwind.config.ts  postcss.config.js
  eslint.config.js  .prettierrc  playwright.config.ts  vercel.json  README.md
  public/            favicon.svg  og.png
  scripts/
    build-fixtures.mjs     # SYNTHETIC: builds mock fixtures from CSVs
    mockups.mjs            # Playwright PNG export + contact sheet
    contract-live.mjs      # validates live /api against types and /openapi.json
  mockups/
    01-onboarding.png 02-pick.png 03-browse.png 04-venue.png 05-map.png
    06-heatmap.png 07-vibe-check.png 08-leaderboard.png 09-bounties.png
    10-run-my-night.png 11-owner.png 11-owner-desktop.png 05-map-desktop.png
    contact-sheet.png README.md
  src/
    main.tsx  App.tsx  routes.tsx
    styles/        tokens.css  index.css
    config/        thresholds.ts  env.ts  genres.ts
    api/           types.ts  client.ts  adapters.ts  queries.ts  auth.ts
    state/         prefs.tsx  persona.tsx  demoClock.tsx  offlineQueue.ts
    lib/           geo.ts (haversine, nearest venue)  names.ts  time.ts  mapsLink.ts
    components/
      ui/          Button Chip Card Sheet Slider Toggle Skeleton Toast EmptyState ErrorState Unknown
      demo/        DemoBadge DemoBanner DemoPanel
      venue/       VibeBadge ConfidenceMeter FreshnessTag TrendArrow ReasonList MissingList
                   ScoreTriplet VenueCard VenueCardCompact PickHero OfferCard ReportTimeline
      layout/      AppShell TabBar Header
    screens/
      Onboarding.tsx Pick.tsx Browse.tsx VenueProfile.tsx MapScreen.tsx
      VibeCheck.tsx Leaderboard.tsx Bounties.tsx RunMyNight.tsx OwnerDashboard.tsx NotFound.tsx
    mocks/
      browser.ts  handlers.ts
      fixtures/
        contract-samples/   *.json (copied from CONTRACTS.md examples)
        synthetic/          syn_venues.json syn_states.json syn_recommendations.json
                            syn_reports.json syn_leaderboard.json syn_bounties.json
                            syn_owner_dashboard.json syn_plan_night.json syn_heatmap.json
  tests/
    unit/  component/  e2e/
docs/workstreams/frontend.md
docs/synthetic/frontend.md
```

## 3. Interfaces

### Consumed (CONTRACTS.md "HTTP API", base `/api`)
| Endpoint | Screen(s) | Notes |
|---|---|---|
| GET `/health` | app load (warm-up, mode fallback, `demo_now`, `data`) | > 5 s → offer mock mode |
| POST `/auth/demo-login` | persona switcher | `{display_name, role, venue_id?}` → `{token, user_id\|scout_id}` |
| GET `/venues?q&style&genre&launch_only=true&limit&offset&now` | Browse, Vibe-check picker | card shape §G; `X-Total-Count` |
| GET `/venues/{id}?now` | Venue profile | `{venue, state, recent_reports, offers}` (§G) |
| GET `/venues/{id}/state?now` | card refresh | Live Venue State exactly as in CONTRACTS |
| POST `/reports` (bearer) | Vibe check | body: venue_id, crowd, dancing, line_minutes, cover_usd?, music_genre?, lat?, lon? → `{report_id, ts, status, points_pending}` |
| POST `/recommend` | Pick | body = Preferences; response = Recommendation result[] with `rank`, `excluded_reason` |
| POST `/plan-night` | Run My Night | Preferences + `n_stops`, `exclude_venue_ids`; stop shape §F |
| POST `/feedback` (bearer) | feedback prompt | syn_feedback fields minus id/recommended_at |
| GET `/scouts/leaderboard?now` | Leaderboard | row shape §G |
| GET `/bounties?now` | Bounties | syn_bounties + `venue_name` |
| GET `/owner/{id}/dashboard?now` | Owner | synthetic for now |
| POST `/owner/{id}/updates` (bearer, owner) | Owner | `syn_venue_updates` fields minus id/ts |
| GET `/heatmap?now&by=hour` | Map | `[{venue_id, lat, lon, hour?, vibe_score, confidence, n_reports, is_synthetic}]` |

### Provided
- Public routes/deep links (PRD F7), used by integration's demo script and share links.
- `frontend/mockups/*.png`: the course deliverable.
- A deployed URL plus `.env.example` documenting the §H names: `VITE_API_MODE`,
  `VITE_API_BASE`, `VITE_DEMO_NOW`, `VITE_FEATURE_ROUTING`, and `VITE_FEATURE_HEATMAP`.

## 4. State and data fetching
- TanStack Query keys: `['venues', filters, now]`, `['venue', id, now]`,
  `['recommend', prefsHash, now]`, `['heatmap', now]`, `['leaderboard', now]`,
  `['bounties', now]`, `['owner', id, now]`, `['plan', prefsHash, n, now]`.
- `staleTime` 60 s. `refetchInterval` 120 s on Pick and Map while the tab is visible.
  POST `/reports` invalidates `venue`, `venues`, `recommend`, and `heatmap`.
- Contexts: `PrefsContext` (persisted `na.prefs.v1`), `PersonaContext` (`planner|scout|owner`,
  demo-login token + `scout_id` / `venue_id`, persisted `na.persona.v1`; token in
  `localStorage`, 24 h), `DemoClockContext` (`now` ISO: URL `?now=` > demo panel >
  `VITE_DEMO_NOW` > `health.demo_now`, in `sessionStorage`).
- Mock mode: MSW starts before render when `VITE_API_MODE=mock` or `?mock=1`. Handlers
  filter fixtures by `now` (they return the report snapshot nearest to `now`). POST handlers update an in-memory copy (a new report raises that venue's n_reports and confidence by a fixed demo step), so the demo loop in §7 step 5 works offline.

## 5. Synthetic datasets needed
All rows carry `is_synthetic: 1`, live in `src/mocks/fixtures/synthetic/`, and are
registered in `docs/synthetic/frontend.md`.

| Fixture | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `syn_venues.json` | venue cards (35) | `build-fixtures.mjs`: real name/address/lat/lon from `data/launch_venues.csv`, joined to live-sim `syn_venue_attributes.csv` if present, else seeded random style/genres/price (seed 42) | GET `/api/venues` (backend from `venues` + claimed owner profiles) | set `VITE_API_MODE=live`, delete fixture, remove handler |
| `syn_states.json` | Live Venue State (incl. `display`) per venue every 30 min, Sat Nov 14 20:00–03:00 (23:30 = DEMO_NOW) | copied from live-sim `data/synthetic_live/demo_night_snapshots.csv` (CONTRACTS §J; already recs-computed). If missing, seeded values with ~20% `null` fields | `recs.live_state.compute_all` via `/api/venues/{id}/state` | as above |
| `syn_recommendations.json` | `/recommend` results for 3 preset prefs (hip-hop dancers, cocktail chill, cheap & close) | hand-authored ranking over syn_states with plausible reasons/missing; 3 excluded with reasons | `recs.scoring.recommend` via `/api/recommend` | as above; delete preset matching in handler |
| `syn_reports.json` | recent scout reports per venue | sampled from live-sim reports, else seeded (crowd 1–5, dancing 0–2, line 0–40) | `syn_scout_reports` → real `scout_reports` table | as above |
| `syn_leaderboard.json` | top 25 scouts | from live-sim `syn_scouts.csv`, else 25 seeded names "Scout ####" | `/api/scouts/leaderboard` over real scouts | as above |
| `syn_bounties.json` | 6 open bounties | from live-sim `syn_bounties.csv`, else seeded on low-confidence venues | `/api/bounties` | as above |
| `syn_owner_dashboard.json` | owner KPIs + demand by hour 18:00–03:00 | seeded curve peaking 23:00–00:00, scaled per venue | backend analytics on real views/taps/reports | as above |
| `syn_plan_night.json` | 3-stop plans for the 3 presets | hand-picked nearby venues, walk minutes from haversine at 5 km/h | `recs.routing.plan_night` via `/api/plan-night` | as above |
| `syn_heatmap.json` | heatmap points per 30-min snapshot; `by=hour` uses the HH:30 snapshot (§J) | derived from syn_states + venue lat/lon | `/api/heatmap` | as above |
| placeholder copy | demo persona names for demo-login | hard-coded, `// SYNTHETIC:` marked | real accounts | delete constants once real login exists |

Real public fields (name, address, lat, lon, noise_complaints) are not synthetic, but a
fixture that mixes them with synthetic fields is still flagged `is_synthetic: 1` as a whole.

## 6. Test plan
| Level | Tool | What | Gate |
|---|---|---|---|
| Static | `tsc --noEmit`, ESLint (jsx-a11y) | types, a11y lint, no hex literals, no `any` | every commit |
| Unit | Vitest | client query/`now`, adapters/null, names cleaner, geo nearest, prefs reducer, offline queue | every commit; ≥ 70% coverage |
| Component | Vitest + RTL | domain components with null / low-confidence / stale / synthetic props; VibeCheckForm submits the right body | every commit |
| Contract | Vitest | `contract-samples/*.json` satisfy type guards; `contract:live` against backend | T4; T16 |
| E2E | Playwright 390×844, mock mode | flows in RULES §5; vibe check in ≤ 10 s of scripted steps; badge on every route | before push |
| A11y | axe-core in Playwright | 0 serious/critical violations per route | T19 |
| Perf | Lighthouse CLI with Chromium at `/opt/pw-browsers/chromium` | Perf ≥ 85, A11y ≥ 95, initial JS ≤ 250 KB gzip | T20 |
| Usability | 5 hallway tests (research supplies recruits) | M1–M3 from PRD §8 | Nov 15–16 |

## 7. Demo script (≈ 4 min, phone-size window, `?demo=1`)
1. **Open** the Vercel URL. The DemoBanner reads "Demo data: simulated Saturday,
   Nov 14". The clock starts at DEMO_NOW **23:30**. Rewind to 22:30 for the pick.
2. **Onboarding:** pick hip-hop + r&b, dancing on, crowd 4, cover ≤ $20, line ≤ 15 min,
   1.5 km, group of 4. Save.
3. **Tonight pick:** read the hero card aloud (match 91, vibe 78, confidence "Good",
   "updated 12 min ago", reasons, missing: "cover not reported tonight"). Open "Show 3
   excluded" and note one was dropped for a 30-min line.
4. **Map:** turn on Heat and drag the time slider 22:30 → 23:30 → 01:00 to show the energy
   moving. Tap a hollow (low-confidence) dot.
5. **Switch persona → Scout.** A bounty on that low-confidence venue is worth 50 pts. Do
   the vibe check in under 10 s with a visible timer. Toast: "+50 pts pending". Return to the map:
   the dot is now filled and confidence went up.
6. **Leaderboard:** the demo scout moves up.
7. **Switch persona → Owner (Mehanata Bulgarian Bar).** Post "$10 cover before midnight,
   DJ Balkan Beat". The preview card updates. KPI tiles + demand curve (badged demo).
8. **Back to Planner → Run My Night** (if T17 is done): a 3-stop plan with walk times.
9. **Close:** point to the "demo data" badges and say every synthetic piece is listed in
   `docs/synthetic/frontend.md` with swap steps.

Fallback: if Render is cold or down, the app runs the same script in mock mode (`?mock=1`).
