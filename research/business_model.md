# Business model and pricing hypotheses

Everything on this page is a **hypothesis**. Prices and rates are `[PLACEHOLDER]`
until tested; none is based on real interviews (none run as of 2026-11-17).
Competitor reference points are from `research/competitors.csv` (real desk research).

## Who pays

- **Consumers (groups):** free. No product in the matrix charges consumers for
  discovery; the event platforms make money from ticket fees instead.
- **Scouts:** free and *rewarded* with perks the venues fund (skip the line,
  free drink, cover waiver). Points cost us nothing until they are redeemed.
- **Venues:** the paying side. Rally's model (venues claim pages but can't
  override user reports) is the closest analogue we found.

## Venue tiers

| Tier | Price `[PLACEHOLDER]` | Includes | Why a venue would pay |
|---|---|---|---|
| Free claimed profile | $0 | Claim the profile, edit hours and style, post cover/DJ/genre updates (official source, weighted separately from Scouts), reply to disputes | Gets correct info in front of groups who are deciding now |
| Pro | $49 / month | Owner dashboard: views, taps, saves, recommendation appearances, demand by hour (`/api/owner/{id}/dashboard`), benchmark against the LES average | Staffing and promo timing; proof the app sends people |
| Offers (performance) | $1 per redeemed offer, or 10% of offer value, capped `[PLACEHOLDER]` | Time-boxed offers shown to matching groups (`offer_expires_at`), Scout bounties funded by the venue | Pay only when someone walks in |

Guardrails (product, not pricing): paying never changes `vibe_score` or
`confidence`. Sponsored placement is labelled. Venues can't edit or delete
Scout reports, only dispute them (`syn_disputes`).

## Unit economics (illustrative, all `[PLACEHOLDER]`)

| Input | Value | Note |
|---|---|---|
| LES launch venues | 35 | `data/launch_venues.csv` |
| Claimed profile rate | 40% → 14 venues | test T1 |
| Free → Pro conversion | 20% of claimed → ~3 venues | test T2 |
| Pro MRR | 3 × $49 = $147 | |
| Offer redemptions / venue / month | 30 at $1 across 14 claimed venues | test T3 |
| Offer revenue / month | 14 × 30 × $1 = $420 | |
| **Revenue / month (LES only)** | **≈ $567** | |
| Scout perk cost to us | $0 directly (venues fund perks); points platform cost ≈ hosting | |
| Hosting (Render free tier + SQLite/Postgres hobby) | ≈ $0–25 / month | depends on backend deploy |
| CAC for a venue | walk-in sales, ~1 hour per venue of team time | no budget |

Takeaway: one zip code does not make a business. The LES is a test of the
mechanism, and the economics only matter if the claim/convert/redeem rates hold
across about 10 nightlife zip codes (≈ 350+ venues → ≈ $5–6k MRR at these rates).

## Hypotheses, falsification tests and thresholds

| ID | Hypothesis | Test | Kill if `[PLACEHOLDER]` |
|---|---|---|---|
| T1 | Venues will claim a free profile and post updates | Walk-in pitch to 10 LES venues and count claims plus ≥ 1 update/week for 3 weeks | < 3 of 10 claim, or < 2 post weekly |
| T2 | Operators will pay for demand analytics | In operator interviews (H10), Van Westendorp on the Pro dashboard mock, then a "pay $49 to keep it after a 30-day trial" ask | < 2 of 5 at ≥ $49/mo, or 0 trial-to-paid |
| T3 | Offers drive walk-ins that venues will pay for | 4-week pilot with 2–3 venues: redemption codes shown in-app, counted at the door | < 10 redemptions / venue / month, or venue won't pay $1 each |
| T4 | Perks bring in enough Scouts | Survey Q15–17 (H7/H8), then a pilot with a venue-funded "skip the line" bounty | < 20% would send ≥ 1 report/night, or a pilot night gets < 1 report/venue/hour at peak |
| T5 | Consumers come back weekly | Pilot cohort retention (`syn_feedback` → real `feedback`) | < 30% week-2 return among first-week users |
| T6 | Paying doesn't buy ranking (trust holds) | Survey Q12 trust cue plus concept test: show a sponsored label and ask about trust | > 30% say the sponsored label makes them distrust all results |

## Not pursued (and why)

- **Consumer subscription:** no consumer pays for discovery among the 20
  products we found, so we'd be competing with free.
- **Selling data to third parties:** a trust risk, it conflicts with storing no
  raw GPS (`distance_m` only), and scraped-data competitors can't do it either.
- **Using complaint risk as a venue score:** the 311 noise-complaint model is a
  neighborhood-relations signal, not a quality signal, and is never sold as one.
