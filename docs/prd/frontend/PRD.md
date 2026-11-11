# PRD — frontend (Nightlife Autopilot web app + mockups)

Workstream: `frontend` · Branch: `nightlife/frontend` · Owns: `frontend/`
Status: planning (no code yet) · Last updated: 2026-11-11

## 1. Problem

A group standing on a Lower East Side corner at 11:30 pm has no good way to
answer "where should we go *right now*?". Review apps describe venues in
general, not tonight; friends' texts are slow and partial. The data and model
workstreams will produce a Live Venue State (vibe, confidence, freshness) and
ranked recommendations, but none of that is useful until a group can see it in
a fast, trustworthy, phone-first UI, and until Scouts and venue operators have
a way to feed it.

The frontend is the only part of the system users touch. It must:
- turn scores into a decision in under a minute (one "Tonight pick" plus
  alternatives, each with plain reasons and how fresh the info is);
- make it easy (≤ 10 s) for a Scout to send a vibe check;
- give a venue operator a place to post updates/offers and see demand;
- be honest: show confidence and freshness, show what's missing, and badge
  every piece of synthetic data as "demo data".

## 2. Goals and non-goals

### Goals (by Nov 17 integration)
1. G1 — A deployed (Vercel) mobile-first React app covering the MVP screens,
   running against the real backend API or a built-in mock API.
2. G2 — Nov 10 mockup deliverable: exported PNGs of every screen (see §6).
   *Nov 10 has passed as of this plan (Nov 11); see Risks R1.*
3. G3 — Every displayed number traceable to a CONTRACTS.md field; no
   favourable defaults for missing data (`null` → "not reported").
4. G4 — "Demo data" badge everywhere `is_synthetic` is true.
5. G5 — Demo replay: a time control that sets `now=<ISO>` on read endpoints so
   the class demo can play back a simulated Saturday night.

### Non-goals
- Native iOS/Android apps; push notifications; offline mode beyond a cached
  last result.
- Real authentication / accounts (MVP uses a pick-a-demo-user / demo-scout /
  demo-owner switcher; see backend's auth decision).
- Payments, booking, reservations, cover purchase.
- Any scoring logic in the browser. Ranking, vibe, confidence, match and
  routing come from the backend (`recs/`). The mock API returns precomputed
  fixtures; it does not re-implement scoring.
- Venues outside the 35 launch venues (search shows only `launch_only=true`
  for MVP).
- Photo/video upload in vibe checks.

## 3. Users

| User | Context | Primary job on the app |
|---|---|---|
| Group planner ("Planner") | 21–30, on phone, with 2–6 friends, Thu–Sat 9 pm–2 am, LES | Pick a place now that fits the group; avoid long lines/high cover |
| Group member | Gets a shared link | See the pick and why; agree |
| Scout | Already at a venue; wants points/status | Send a 10-second vibe check; claim bounties; see rank |
| Venue operator ("Owner") | Bar manager, on phone or laptop, before/during service | Post cover/DJ/offer; see views, taps, reports, demand |
| Demo presenter | Team member in class | Replay a night, switch personas, show synthetic vs. real |

## 4. User stories and acceptance criteria

IDs are referenced by OUTLINE.md tasks and tests.

### Onboarding / preferences
**US-01** As a Planner I set my group's preferences and limits once so picks fit us.
- AC1: Form fields map 1:1 to the Preferences JSON in CONTRACTS.md: genres
  (multi-select chips), want_dancing (toggle), crowd_pref (1–5 slider:
  "chill" → "packed"), max_cover_usd (0/10/20/30/any), max_line_minutes
  (0/10/15/30/any), max_distance_km (0.5/1/1.5/3), group_size (1–12).
- AC2: Location from browser geolocation; if denied/unavailable, default to
  the LES centroid `40.7178, -73.9893` and show "Using LES center".
- AC3: Prefs persist in `localStorage` (key `na.prefs.v1`) and can be edited
  from any screen via a header "Prefs" chip.
- AC4: Complete-able in ≤ 4 taps using defaults ("Skip — use defaults").

### Tonight pick
**US-02** As a Planner I see one best pick right now with reasons, so we decide fast.
- AC1: Calls `POST /api/recommend` with prefs; shows the top non-excluded result
  as a hero card: name, match_score, vibe_score, confidence meter, distance,
  2–4 `reasons`, all `missing` items, freshness ("updated 12 min ago").
- AC2: Below the hero, the next 4 results as compact cards ("Also good").
- AC3: Excluded results are hidden by default; a "Show 3 excluded" link reveals
  them with the exclusion reason greyed.
- AC4: If confidence < display threshold (placeholder **0.35**, final value
  from `docs/specs/`), vibe shows as "Low info" rather than a number.
- AC5: Freshness > **90 min** (placeholder) shows "stale" styling.
- AC6: Pull-to-refresh / Refresh button refetches; auto-refresh every
  **120 s** while visible.
- AC7: "Share pick" copies a URL `/v/{venue_id}?from=pick` to clipboard.

### Browse: cards, filter bar, search
**US-03** As a Planner I browse and filter all launch venues.
- AC1: `GET /api/venues?launch_only=true` with `q`, `style`, `genre` mapped
  from search box and filter chips; debounced 250 ms.
- AC2: Sort options: Vibe (default), Distance, Name. Sorting is client-side on
  returned fields.
- AC3: Each card: display name, style, genres, vibe badge, confidence, line,
  cover, freshness, demo badge if synthetic.
- AC4: Empty state with "Clear filters".

### Venue profile
**US-04** As a Planner I open a venue to see live state, recent reports and offers.
- AC1: `GET /api/venues/{venue_id}`; shows header (name, address, style, price
  level), live state block (crowd, dancing, line, cover, music, trend arrow,
  n_reports, sources), recent reports timeline (time ago, scout level,
  fields), active offers with expiry, "Directions" link (Google/Apple maps URL).
- AC2: Complaint-risk, if shown, is labelled exactly "311 noise complaint
  history" with the count — never as a quality or vibe signal.
- AC3: "Send vibe check" button (Scout mode) pre-selects this venue.

### Map / heatmap
**US-05** As a Planner I see where the energy is on a map.
- AC1: `GET /api/heatmap`; MapLibre map with dark basemap; each venue a dot
  sized by confidence and coloured by vibe_score; low-confidence dots hollow.
- AC2: Tap dot → bottom sheet mini-card → profile.
- AC3: Toggle "Heat" renders a heat layer weighted by vibe × confidence.
- AC4: Time slider (demo mode) changes `now` and refetches.

### Scout: 10-second vibe check
**US-06** As a Scout I report a venue's vibe in ≤ 10 s.
- AC1: One screen, thumb-reachable: venue (auto-picked nearest within 75 m,
  else picker), crowd 1–5 (5 big buttons), dancing none/some/lots, line
  minutes (0/5/10/20/30+ chips), optional cover and music genre (collapsed).
- AC2: Submit sends `POST /api/reports` with the CONTRACTS.md fields;
  `verified_presence` = 1 only if geolocation within **75 m** (placeholder)
  of venue, else 0.
- AC3: Median task time in usability test ≤ 10 s from screen open to submit
  (measured with a timer in the test build).
- AC4: Success toast shows points earned (from response if provided; otherwise
  "+10 pts (demo)" with badge).
- AC5: Offline/failed submit is queued in `localStorage` and retried once.

### Scout leaderboard + bounties
**US-07** As a Scout I see my rank and open bounties.
- AC1: `GET /api/scouts/leaderboard` → ranked list (rank, display_name, level,
  points, reputation as 1–5 stars).
- AC2: `GET /api/bounties` → open bounties with venue, points, reason, age;
  tap → vibe check for that venue.
- AC3: The current demo scout is highlighted and pinned if outside top 20.

### Run My Night (later, stretch for Nov 17)
**US-08** As a Planner I get an ordered 2–4 stop plan.
- AC1: `POST /api/plan-night` with prefs + `n_stops` (default 3).
- AC2: Vertical timeline of stops with suggested arrival times, walk minutes
  between stops, reasons per stop; mini map with route polyline.
- AC3: "Swap stop" re-requests excluding that venue (requires contract change
  CR-3; until then, hidden).

### Owner dashboard
**US-09** As an Owner I post an update and see demand.
- AC1: `GET /api/owner/{venue_id}/dashboard` → KPI tiles (views, taps,
  reports tonight, recommendation appearances), hourly demand chart, recent
  reports list. Whole dashboard carries the demo badge while synthetic.
- AC2: Update form → `POST /api/owner/{venue_id}/updates` with cover_usd, dj,
  genres, event, offer, offer_expires_at; preview of how the card will look.
- AC3: Owner persona picks venue from a dropdown (no real claim flow in MVP).

### Cross-cutting
**US-10** As a demo presenter I replay a simulated night and switch personas.
- AC1: Hidden demo panel (`?demo=1` or 5 taps on logo): persona switcher
  (Planner / Scout / Owner), time picker that sets global `now`, API mode
  (live / mock), and "Show synthetic outline" toggle.
- AC2: Every read request includes `now` when set.

**US-11** As any user I can tell demo data from real data.
- AC1: `<DemoBadge/>` renders on any card/section whose data has
  `is_synthetic: 1|true`, and globally in mock mode.

## 5. Scope

| Feature | MVP (Nov 17) | Later |
|---|---|---|
| Onboarding prefs | ✅ | multi-member group merge, compatibility score |
| Tonight pick + reasons + freshness | ✅ | personalized from feedback |
| Venue cards, filter bar, search | ✅ | all 1,727 bars |
| Venue profile | ✅ | photos, claimed-profile badge |
| Map with dots | ✅ | |
| Heat layer + time slider | ✅ (demo mode) | real-time availability heatmap |
| 10-second vibe check | ✅ | photo, dispute flow |
| Leaderboard + bounties | ✅ | rewards redemption |
| Owner dashboard + update form | ✅ | claim/verify flow, offer analytics |
| Run My Night | stretch | swap stops, group voting |
| Post-visit feedback prompt | stretch (writes `syn_feedback` shape; needs CR-2) | ✅ |
| Auth | demo persona switcher | real login |

## 6. Requirements

### Functional
- F1 All network access goes through one typed API client `src/api/client.ts`
  whose types mirror CONTRACTS.md; screens never call `fetch` directly.
- F2 `VITE_API_MODE=mock|live`; mock mode serves fixtures from
  `src/mocks/` via MSW (Mock Service Worker) with the same routes.
- F3 `VITE_API_BASE_URL` (default `/api` proxied in dev to
  `http://localhost:8000`).
- F4 Global `now` (demo replay) added as query param to every GET.
- F5 Null fields render "not reported", never 0 or a default.
- F6 Venue display names: cleaned client-side from SLA legal names
  (strip `LLC`, `INC`, `CORP`; title-case all-caps) unless backend sends a
  `display_name` (CR-1). Example: `ATTABOY COCKTAILS LLC` → `Attaboy Cocktails`.
- F7 Deep links: `/`, `/pick`, `/browse`, `/map`, `/v/:venueId`, `/scout`,
  `/scout/leaderboard`, `/plan`, `/owner/:venueId`, `/onboarding`.

### Non-functional
- N1 Mobile-first: designed at 390×844; works 360–1440 px wide; no horizontal
  scroll; tap targets ≥ 44 px.
- N2 Performance: Lighthouse mobile Performance ≥ **85**, initial JS
  ≤ **250 KB gzip** (map chunk lazy-loaded), LCP ≤ 2.5 s on simulated 4G.
- N3 Accessibility: WCAG 2.1 AA contrast on dark theme; all controls
  keyboard- and screen-reader-labelled; vibe colour never the only cue
  (number or label alongside); Lighthouse a11y ≥ **95**.
- N4 Resilience: every screen has loading (skeleton), empty, and error
  (retry) states; API errors don't blank the app.
- N5 Privacy: precise location stays in the browser except the `lat/lon` sent
  in prefs and vibe-check presence check; no analytics SDKs in MVP.

### Design system (dark nightlife theme)
- Background `#0B0B12`, surface `#16161F`, raised `#20202C`, text `#F3F3F7`,
  muted `#9A9AB0`, accent (neon magenta) `#FF3D8B`, secondary (electric cyan)
  `#2EE6D6`, warn `#FFB020`, danger `#FF5A5A`.
- Vibe scale (0–100) 5-step ramp: `#3A3A55` (dead) → `#5B4BDB` → `#A63DFF`
  → `#FF3D8B` → `#FFB020` (on fire); labels Dead/Quiet/Warming/Lively/Packed.
- Confidence: 4-bar meter (0–.25–.5–.75–1) + text "Low/Some/Good/High".
- Type: Inter (UI), Space Grotesk (numbers/headings); scale 12/14/16/20/28/40.
- Radius 12/20; spacing 4-pt grid; elevation via border `#2A2A3A`, no shadows.
- Motion: 150 ms ease-out; respect `prefers-reduced-motion`.
- A light theme is out of scope; the app forces dark (`color-scheme: dark`).

### Mockup deliverable (Nov 10, late)
- Format: one PNG per screen at 390×844 @2x (780×1688), plus a desktop
  1440×900 PNG for Owner dashboard and Map; file names
  `frontend/mockups/NN-screen-name.png`; contact sheet
  `frontend/mockups/contact-sheet.png`; short `frontend/mockups/README.md`.
- Produced from the running app in mock mode via a Playwright script
  (`npm run mockups`), so mockups and app never diverge.

## 7. Dependencies on other workstreams

| Workstream | What frontend needs | When | Fallback if late |
|---|---|---|---|
| specs | confidence display threshold, freshness "stale" cutoff, vibe label bands, scout points per report, verified-presence radius | before task T6 | placeholders in `src/config/thresholds.ts` (values in §4) |
| research | interview findings on which reasons/filters matter; usability-test recruits | Nov 13 | ship current order |
| tableau | none at runtime; may reuse owner-dashboard KPI definitions | — | — |
| live-sim | `syn_*` CSVs (esp. a full Saturday night) to build mock fixtures and the replay demo | Nov 13 | frontend hand-writes small fixtures (see OUTLINE §5) |
| ml-recs | real `reasons` / `missing` strings, routing output shape for plan-night | Nov 14 | fixture strings |
| backend | all endpoints in CONTRACTS.md live on Render with CORS for the Vercel domain; response shapes for venue card/profile/dashboard/leaderboard/plan-night (not fully specified in CONTRACTS) | shapes Nov 13, deploy Nov 15 | mock mode in production build with banner |
| frontend | — | — | — |
| coursework | none | — | — |
| integration | Vercel project + env vars, final API URL, demo script slot | Nov 16 | deploy preview URL |

## 8. Success metrics

Demo/class targets (synthetic-evaluated unless noted):
- M1 Time to decision: median ≤ **45 s** from opening `/pick` (prefs saved) to
  tapping Directions/Share, in ≥ 5 hallway usability tests.
- M2 Vibe check time: median ≤ **10 s**, ≥ 90% completion without help.
- M3 Comprehension: ≥ 80% of testers correctly explain what "confidence"
  means after seeing the pick card.
- M4 Synthetic honesty: 100% of screens showing synthetic data show the badge
  (automated test).
- M5 Quality bars: Lighthouse mobile Perf ≥ 85, a11y ≥ 95; 0 console errors on
  demo script run.
- Pilot (later, real users): % sessions ending in a pick tap ≥ 40%; scout
  reports per active venue-hour ≥ 2.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Nov 10 mockup deadline already passed | Build static screens in mock mode first (T1–T5), export PNGs by Nov 12; tell the master session |
| R2 | Backend response shapes not specified for cards/profile/dashboard/leaderboard/plan | Define TS types now (OUTLINE §3), file CR-4; adapt in a single `adapters.ts` |
| R3 | Synthetic data mistaken for real in a demo | DemoBadge + mock-mode banner + test M4 |
| R4 | Complaint risk read as "this bar is bad/good" | Fixed label, only on profile, never in ranking UI |
| R5 | Map tiles need an API key / cost | MapLibre + free dark style (CARTO dark-matter via OpenFreeMap or self-host); key-free fallback to an SVG dot plot |
| R6 | Geolocation denied / desktop demo | LES centroid default; demo location presets |
| R7 | CORS / mixed-content between Vercel and Render | `VITE_API_BASE_URL` https only; Vercel rewrite `/api/*` → Render as alternative |
| R8 | SLA legal names look wrong (`Apt 5 LLC`) | name cleaner + CR-1 display_name |
| R9 | Render free-tier cold start (~30–60 s) during demo | warm-up ping on app load + skeletons; demo starts in mock mode if `/api/health` > 5 s |

## 10. Open questions

1. Q1 Can backend add `display_name`, `style`, `genres`, `price_level`, and
   `is_synthetic` to the venue card payload? (CR-1)
2. Q2 What is the exact shape of `GET /api/venues` card, `GET /api/venues/{id}`,
   leaderboard, bounties, owner dashboard, and plan-night stops? (CR-4)
3. Q3 Final values from specs: confidence threshold, stale cutoff, vibe bands,
   points per report, presence radius.
4. Q4 How does the client identify the current scout/owner in MVP — a
   `scout_id` in the POST body, or a header `X-Demo-User`?
5. Q5 Does `/api/recommend` return excluded items (with a reason field) or omit
   them? CONTRACTS shows `excluded: false` but no `excluded_reason`. (CR-5)
6. Q6 Which map style/tiles are acceptable for the class deploy (key-free)?
7. Q7 Is a Planner's shared link expected to open the same pick for group
   members, or re-run with their location?
8. Q8 Who owns the Vercel account (Ryan) and the final domain?

## 11. Assumptions (made without asking)
- A1 All 35 launch venues are `Bar/Tavern` in the CSV; "club" style comes only
  from `syn_venue_attributes.style`.
- A2 Backend sends the Live Venue State nested as `state` inside venue cards.
- A3 Points/levels are computed server-side; the frontend only displays them.
- A4 The demo runs on a phone-sized browser window projected in class.
- A5 Node 20 LTS is available locally and on Vercel.

## 12. Contract change requests
(Proposed; not applied to CONTRACTS.md. Integration/master to decide.)

- **CR-1** Venue card adds `display_name`, `style`, `genres[]`,
  `price_level`, `typical_cover_usd`, `lat`, `lon`, `is_synthetic`.
- **CR-2** `POST /api/feedback` (body = `syn_feedback` fields minus id/
  recommended_at) for the post-visit prompt.
- **CR-3** `POST /api/plan-night` accepts `exclude_venue_ids: string[]`.
- **CR-4** Document response shapes for: venue card, venue detail
  (`{venue, state, recent_reports[], offers[]}`), leaderboard item
  (`{rank, scout_id, display_name, level, points, reputation}`), bounty item
  (`syn_bounties` fields + `venue_name`), owner dashboard
  (`{venue_id, views, taps, reports_tonight, rec_appearances, demand_by_hour:[{hour, value}], is_synthetic}`),
  plan-night stop (`{order, venue_id, name, arrive_at, walk_minutes_from_prev, reasons[], lat, lon}`).
- **CR-5** Recommendation result adds `excluded_reason: string|null`.
- **CR-6** `POST /api/reports` response returns `{report_id, ts, points_awarded}`.
- **CR-7** Every response object carries `is_synthetic` (not only Live Venue State).
