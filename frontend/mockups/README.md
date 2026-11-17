# Frontend mockups

Exported from the running app (mock mode, MSW fixtures) with `npm run mockups`
(`scripts/mockups.mjs`, Playwright + preinstalled Chromium) at the demo moment
`now=2026-11-14T23:30:00-05:00` (CONTRACTS §B). The mockups and the app come from the same code, so they can't drift apart.
**All data shown is synthetic**; every screen shows the "demo data" banner/badges.

| File | Screen | Route | Size |
|---|---|---|---|
| `01-onboarding.png` | Group preferences (US-01) | `/onboarding` | 390×844 @2x |
| `02-pick.png` | Tonight's pick + also good + 3 excluded (US-02) | `/tonight` | 390 @2x, full page |
| `03-browse.png` | Browse, filters, cards (US-03) | `/browse` | 390×844 @2x |
| `04-venue.png` | Venue profile (US-04) | `/venue/0370-21-116653` | 390 @2x, full page |
| `05-map.png` | Map, dots by vibe/confidence (US-05) | `/map` | 390×844 @2x |
| `06-heatmap.png` | Map with heat layer on (US-05) | `/map` | 390×844 @2x |
| `07-vibe-check.png` | 10-second vibe check on a bounty venue (US-06) | `/scout?venue=…` | 390×844 @2x |
| `08-leaderboard.png` | Scout leaderboard (US-07) | `/scout/leaderboard` | 390×844 @2x |
| `09-bounties.png` | Open bounties (US-07) | `/scout/bounties` | 390×844 @2x |
| `10-run-my-night.png` | Run My Night, 3 stops (US-08, stretch) | `/plan` | 390 @2x, full page |
| `11-owner.png` | Owner dashboard + update form (US-09) | `/owner/0370-23-127248` | 390 @2x, full page |
| `11-owner-desktop.png` | Owner dashboard, desktop | same | 1440×900 |
| `05-map-desktop.png` | Map + heat, desktop | `/map` | 1440×900 |
| `contact-sheet.png` | All of the above | — | 1800 wide |

Map tiles: OpenFreeMap dark style (© OpenMapTiles, data © OpenStreetMap contributors).
Regenerate: `cd frontend && npm run mockups` (about 1 min).
