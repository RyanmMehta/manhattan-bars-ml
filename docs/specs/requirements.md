# Requirements — user stories, acceptance criteria, traceability

Purpose: every MVP and Later feature as a testable story, mapped to a screen (frontend) and endpoint (backend).
Status: agreed (MVP scope fixed for the Nov 17 demo).
Last updated: 2026-11-17

IDs `US-<AREA>-<n>`. Acceptance criteria are Given/When/Then. Copy strings in quotes are normative.
Formulas live in [SCORING.md](SCORING.md); trust rules in [scout-trust.md](scout-trust.md).

## 1. Onboarding and preferences
**US-ON-1 (MVP)** As a planner I set genres, dancing yes/no, crowd level, max cover, max line, max distance and group size in ≤ 30 s.
- Given first launch, when I finish onboarding, then a Preferences object (Contracts) is stored locally and sent with `/api/recommend`.
- Given I skip a field, then it takes the default: genres `[]`, `want_dancing` null, `crowd_pref` 3, `max_cover_usd` 30, `max_line_minutes` 20, `max_distance_km` 1.5, `group_size` 2 (PARAMETERS `default_*`).
- Given geolocation is denied, then lat/lon = Delancey/Essex (40.7185, −73.9878).
- Given first launch, then a 21+ notice is shown before onboarding.

**US-ON-2 (MVP)** I edit limits from the filter bar without redoing onboarding.
- When I change a limit, then the pick list refreshes with the new Preferences within 1 s on local.

## 2. Tonight pick
**US-TP-1 (MVP)** I see one top pick plus 2 alternates with match, vibe, confidence, distance, reasons and missing.
- Then order equals `/api/recommend` order; excluded venues are never in the top 3; "N hidden by your limits" shows the excluded count.

**US-TP-2 (MVP)** Each score shows freshness ("12 min ago") and follows the display rule (SCORING §5).
- Given `display=show`, then the vibe number, label (Chill/Lively/Packed) and "N reports, M min ago" show.
- Given `display=low`, then the vibe is greyed with "low confidence".
- Given `display=none`, then "No fresh reports" and a "Be the Scout" CTA show; no vibe number.
- Given `freshness_minutes > 60`, then a "stale" tag shows.

**US-TP-3 (MVP)** Every screen with synthetic data shows the "demo data" badge.
- Given any response with `is_synthetic: true` or header `X-Data: synthetic|mixed`, then the badge is visible.

## 3. Venue cards, filters, search
**US-VC-1 (MVP)** Cards show name, style, distance, vibe (display rule), trend arrow, line/cover if known.
- Given `trend` null, then no arrow. Given line/cover null, then the field is hidden (not "0").

**US-VC-2 (MVP)** Filters: style, genre, open now, "has fresh reports" (conf ≥ 0.40), launch only.
- Then filters map to `/api/venues?style=&genre=&launch_only=` (open-now and fresh are client-side on returned state).
- Given no results, then "No venues match — loosen filters".

**US-VC-3 (MVP)** Search by name: case-insensitive substring, ≥ 2 chars, results ≤ 300 ms on local (`/api/venues?q=`).

## 4. Venue profile
**US-VP-1 (MVP)** Profile shows public facts (address, hours if known, inspection grade, "311 noise-complaint risk" labelled "complaint risk, not quality"), live state, last 5 reports (age, crowd, dancing, line, scout display name + level), current offers.
- Then data comes from `/api/venues/{venue_id}`; no scout identity beyond display name.

**US-VP-2 (MVP)** An operator-claimed profile (`is_claimed=1`) shows a "claimed" check.

## 5. Scout mode
**US-SC-1 (MVP)** As a Scout I submit crowd (1–5), dancing (none/some/lots), line (0/5/10/20/30+), optional cover and genre in ≤ 10 s / ≤ 4 taps.
- When I submit with a Bearer token from `POST /api/auth/demo-login`, then `POST /api/reports` returns 201 `{report_id, ts, status, points_pending}`; server sets `scout_id`, `ts`, `verified_presence`, `distance_m`, `status=pending`.
- Given genre, then it must be one of the 17 slugs; otherwise 422.

**US-SC-2 (MVP)** Rate limits (scout-trust §2 #1) return 429 with the friendly message.

**US-SC-3 (MVP)** Given GPS allowed and within 150 m, then `verified_presence=1`; only `distance_m` is stored.

**US-SC-4 (MVP)** After submitting I see points pending and my new rank.

## 6. Rewards, leaderboard, bounties
**US-RW-1 (MVP)** Leaderboard: top 20 by points this week and all-time; display name, level, reports, reputation band (`/api/scouts/leaderboard`).

**US-RW-2 (MVP)** Bounties list open bounties with `venue_name`, points, `expires_at` (`/api/bounties`); claimed implicitly by the first qualifying report.

**US-RW-3 (MVP)** Points become "earned" after the 30-min hold if the report is not flagged.

## 7. Owner dashboard
**US-OW-1 (MVP)** As an operator I see views, taps, saves, reports tonight, rec appearances and demand by hour (`/api/owner/{venue_id}/dashboard`), synthetic and badged.

**US-OW-2 (MVP)** I post an update (cover, DJ, genres, event, offer + expiry) via `POST /api/owner/{venue_id}/updates`.
- Then it appears in live state within 1 min (cache ≤ 60 s) and on the profile as "posted by venue".

**US-OW-3 (MVP)** I dispute a scout report (reason required). I cannot submit scout reports for my own venue (403).

**US-OW-4 (MVP)** Owner identity = demo-login with `role=owner, venue_id`; one owner per venue. **Later:** verification flow.

## 8. Later features
**US-HM-1 (Later)** Availability heatmap: launch venues coloured by vibe, opacity by confidence (`/api/heatmap?now=&by=hour`), MapLibre with free tiles; `now=` slider.

**US-CP-1 (Later)** Group compatibility: per-member prefs; group score = mean(member match) − 0.5·std; any member's hard limit excludes.

**US-RL-1 (Later)** Full recommendation list with "why not" (`excluded_reason`) for excluded venues.

**US-RN-1 (Later)** Run My Night: 3 stops with times and walking minutes, each passing limits at arrival (`/api/plan-night`).

## 9. Non-functional
**US-NF-1** p95 `/api/recommend` ≤ 500 ms for 35 venues and 2k reports on the demo host.
**US-NF-2** Mobile-first; usable at 360 px width.
**US-NF-3** No PII beyond display names; no raw GPS stored.
**US-NF-4** Every synthetic dataset follows the Contracts synthetic-data rule; `INCLUDE_SYNTHETIC=0` hides it.
**US-NF-5** `/api/health` returns `{ok, recs, data, demo_now}`; `/openapi.json` is the machine-readable contract.

## 10. Traceability
| Story | Screen (frontend) | Endpoint (backend) | Spec | Phase |
|---|---|---|---|---|
| US-ON-1 | Onboarding | `POST /api/recommend` | PARAMETERS defaults | MVP |
| US-ON-2 | Filter bar | `POST /api/recommend` | — | MVP |
| US-TP-1 | Tonight | `POST /api/recommend` | SCORING §7–9 | MVP |
| US-TP-2 | Tonight, Card | `POST /api/recommend` | SCORING §5 | MVP |
| US-TP-3 | all | all (`is_synthetic`, `X-Data`) | Contracts rule 5 | MVP |
| US-VC-1 | Venue list | `GET /api/venues` | SCORING §5–6 | MVP |
| US-VC-2 | Venue list filters | `GET /api/venues` | — | MVP |
| US-VC-3 | Search | `GET /api/venues?q=` | — | MVP |
| US-VP-1 | Venue profile | `GET /api/venues/{id}` | SCORING §2 offers | MVP |
| US-VP-2 | Venue profile | `GET /api/venues/{id}` | — | MVP |
| US-SC-1 | Scout mode | `POST /api/auth/demo-login`, `POST /api/reports` | scout-trust §2–3 | MVP |
| US-SC-2 | Scout mode | `POST /api/reports` (429) | scout-trust §2 | MVP |
| US-SC-3 | Scout mode | `POST /api/reports` | scout-trust §2 #3 | MVP |
| US-SC-4 | Scout confirmation | `GET /api/scouts/leaderboard` | scout-trust §5 | MVP |
| US-RW-1 | Leaderboard | `GET /api/scouts/leaderboard` | scout-trust §5 | MVP |
| US-RW-2 | Bounties | `GET /api/bounties` | scout-trust §6 | MVP |
| US-RW-3 | Scout profile | `GET /api/scouts/leaderboard` | scout-trust §5 | MVP |
| US-OW-1 | Owner dashboard | `GET /api/owner/{id}/dashboard` | — | MVP |
| US-OW-2 | Owner update form | `POST /api/owner/{id}/updates` | SCORING §1–3 | MVP |
| US-OW-3 | Owner dashboard | dispute (backend admin/script), `POST /api/reports` (403) | scout-trust §4 | MVP |
| US-OW-4 | Owner login | `POST /api/auth/demo-login` | — | MVP |
| US-HM-1 | Map | `GET /api/heatmap` | SCORING §5 | Later |
| US-CP-1 | Group | `POST /api/recommend` | SCORING §7 | Later |
| US-RL-1 | Full list | `POST /api/recommend` | SCORING §8 | Later |
| US-RN-1 | Run My Night | `POST /api/plan-night` | SCORING §10 | Later |
| US-NF-1..5 | — | all | — | MVP |

Feedback (`POST /api/feedback`) feeds visit rate and satisfaction ([pilot-metrics.md](pilot-metrics.md)); the UI asks "Did you go? Rate it" the next time the app opens.
