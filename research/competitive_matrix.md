# Competitive matrix and positioning

**Real desk research.** Source of every cell: `research/competitors.csv`
(20 products, each row with `source_url` and `retrieved_at = 2026-11-17`).
Public pages, press and app-store listings only, read by hand, no scraping.
`?` = unknown: we couldn't verify it, so we didn't guess.

## Matrix

Y = yes, p = partial, N = no.

| # | Product | Status (last seen) | Real-time signal | Crowd-sourced | Group matching | Shows confidence | Venue-side tools | NYC coverage | Reporter incentives | Cost to consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| c01 | BarHop | unknown (?) | Y | Y | N | N | N | ? | N | free |
| c02 | Buzzd | pivoted (2011-04) | Y | Y | N | N | N | Y | N | free |
| c03 | nYtevibe | unknown (?) | ? | ? | ? | ? | ? | ? | ? | ? |
| c04 | What's Playin | unknown (?) | ? | ? | N | N | ? | ? | ? | ? |
| c05 | BarHopper | live (2026-09)¹ | Y | Y | p | N | N | ? | N | free |
| c06 | Google Maps popular times / live busyness | live (2026-08) | Y² | p | N | p³ | p | Y | p | free |
| c07 | Instagram (stories, location tags, Map) | live (2025-08) | p | Y | p | N | Y | Y | p | free |
| c08 | Snap Map | live (2026-07) | Y | Y | p | N | p | Y | p | free |
| c09 | TikTok Local feed | live (2026-02) | p | Y | N | N | p | Y | p | free |
| c10 | Partiful | live (2026-06) | N | N | Y⁴ | N | p | Y | N | free / ticket fees |
| c11 | Resy | live (2026-09) | p⁵ | N | N | N | Y | Y | p | free |
| c12 | DICE (owned by Fever) | live (2026-06) | N | N | N | N | Y | Y | N | ticket fees |
| c13 | Posh | live (2026-03) | N | N | p | N | Y | Y | N | ticket fees |
| c14 | Eventbrite | live (2025-12) | N | N | N | N | Y | Y | N | ticket fees |
| c15 | Yelp | live (2026-10) | p | Y | N | N | Y | Y | p⁶ | free |
| c16 | Beli | live (2026-08) | N | Y | p | p⁷ | N | Y | p | free |
| c17 | Fever | live (2026-05) | N | N | N | N | Y | Y | N | ticket fees |
| c18 | Rally – Live Wait Times (Wait Watch) | live (2026-10)¹ | Y | Y | N | N | p⁸ | ? | p | free |
| c19 | LinePal | live (2025-11) | Y | ? | N | N | ? | ? | ? | free |
| c20 | Sense: Nightlife Statistics | unknown (2023-03) | Y | ? | N | N | ? | ? | ? | free |
| — | **Nightlife Autopilot (planned)** | demo 2026-11-17 | Y | Y | Y | **Y** | Y | LES only | Y | free |

Footnotes
1. Year inferred: the App Store showed a month and day but no year (see csv notes).
2. Aggregated opt-in location history, not reports. Bars with little traffic may show nothing.
3. Relative labels ("busier than usual"), not an explicit confidence or freshness.
4. Matches the group's *plans* (invites/RSVPs), not their preferences against live venue state.
5. Table availability only. No crowd, line or music.
6. Elite program: status, not cash.
7. A personal ranking score (unverified detail), not confidence in live info.
8. Venues can claim pages but can't override user reports. This is the closest model to ours.

Rows with weak evidence: c01, c03 and c04 (we couldn't confirm the product or
its activity), c05 and c18 (year inferred), c12 (date of the anniversary piece),
c14 (we couldn't confirm the acquisition closed), c19 and c20 (store listing only).
Re-check them before any external use.

## What the matrix shows

- **Nobody shows confidence or freshness on live info.** Google gives relative
  busyness and the social apps give raw stories, but no product says "4 reports,
  12 min ago, confidence 0.71". This is our clearest gap, and it is the column
  marked **Y** only for us.
- **Live-crowd apps exist, but they are small single-signal tools.** BarHopper
  (check-in counts), Rally (wait times from the last hour), LinePal and Sense
  (wait times) report crowd or line. None found matches a group's preferences
  (genre, dancing, cover cap, line cap) against that state.
- **The big platforms own planned nights, not "right now."** Partiful, Posh,
  DICE, Fever, Eventbrite and Resy handle invites, tickets and tables. Posh's
  2026 funding pitch names the "what are we doing tonight" problem, which
  suggests the space is contested and moving.
- **Social maps are the de facto substitute.** Instagram Map (2025-08), Snap Map
  and TikTok's Local feed (2026-02) show where friends are and what's posted, but
  with no structured fields (line, cover, genre).

## Why legacy apps likely failed (hypotheses, not findings)

- **Buzzd (pivoted 2011):** *Hypothesis:* it aggregated check-ins it didn't
  own, so it had no unique data and no habit. Per TechCrunch it never gained
  traction and moved to selling to businesses.
- **BarHop / nYtevibe / What's Playin / Sense:** *Hypothesis:* the cold start.
  Live data is worthless until enough reporters exist at each venue each night,
  and a city-wide launch spreads them too thin. Little public trace is left of
  any of them.
- **General hypothesis:** reporters got nothing tangible (no perks, no status),
  so report volume decayed after launch novelty. We test this as H7/H8.

Design responses: launch in one zip (10002, 35 venues) to concentrate reports;
give Scouts tangible perks; show confidence and freshness so sparse data is
honest instead of misleading; give venues a reason to post (demand analytics).

## Positioning statement (≤ 60 words)

> For groups in their 20s deciding where to go out tonight on the Lower East
> Side, who waste time guessing from stale ratings and friends' stories,
> Nightlife Autopilot is a live nightlife guide that matches the group's
> preferences to fresh, crowd-sourced vibe checks. Unlike Google Maps or
> Instagram, it shows how recent and how trustworthy each report is.

(58 words.)

## 2×2 chart spec (for tableau or slides)

- **X axis: freshness of venue info** (left = static/historical, right = live, < 60 min).
- **Y axis: personalization to the group** (bottom = same for everyone, top = matched to the group's stated preferences).
- Placement (qualitative, from the matrix above, not measured):
  - Bottom-left (static, generic): Yelp, Eventbrite, Fever, DICE.
  - Top-left (static, personalized): Beli, Partiful (group plans), Resy.
  - Bottom-right (live, generic): Google Maps live busyness, BarHopper, Rally, LinePal, Sense, Snap Map, Instagram Map, TikTok Local.
  - **Top-right (live, personalized): Nightlife Autopilot** (empty quadrant among the products we found).
- Point marker shape = status (live / dead or pivoted / unknown). A footnote on the
  chart: "Placement is a qualitative judgment from public desk research, 2026-11-17."
- Not synthetic, so no "demo data" badge, but label it "qualitative".

Caveat: complaint risk (the 311 model) is **not** a quality or vibe signal and
is not used in this positioning.
