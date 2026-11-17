# Research: slide-ready bullets (about 2 minutes)

**Slide 1: Who tried this before** (real desk research, 20 products, checked 2026-11-17)
- Buzzd (NYC, real-time city guide) pivoted to B2B in 2011 after never gaining traction (TechCrunch).
- Live-crowd apps still exist but are small: BarHopper, Rally, LinePal, Sense (dormant since 2023).
- The big players own *planned* nights: Partiful, Posh, DICE (now Fever), Eventbrite, Resy.
- The substitute everyone uses: Google live busyness + Instagram / Snap Map / TikTok Local.
- **No one shows how fresh or how trustworthy live info is.**

**Slide 2: Positioning + 2×2**
- "For groups in their 20s deciding where to go out tonight on the LES … unlike Google Maps or Instagram, it shows how recent and how trustworthy each report is."
- 2×2 (freshness × personalization): we sit in the empty top-right quadrant. The placement is qualitative.

**Slide 3: How we'll test it**
- 12 hypotheses with pass/kill thresholds (`research/hypotheses.md`).
- 3 interview guides (consumer 25–30 min, Scout 20 min, operator 25 min) and a 17-question, < 5-minute survey.
- **Real interviews completed: 0** (recruiting starts the week of Nov 17).

**Slide 4: Voice of customer. DEMO DATA** (badge required)
- Tableau dashboard from `research/synthetic/summary_tables.csv`, n = 300 synthetic.
- Shows top decision factors, freshness tolerance and % willing to scout.
- Say out loud: "These numbers are placeholders we generated to build the pipeline. They are not findings."

**Slide 5: Business model** (hypotheses)
- Free claimed profile → Pro $[49]/mo for demand analytics → offers at $[1] per redemption.
- Paying never changes vibe or confidence.
- Each tier has a kill test (T1–T6 in `research/business_model.md`).

**Slide 6: What changes when real data arrives**
- Match weights (ml-recs), the half-life and stale cutoff (specs), and badge copy (frontend) are all marked as research placeholders.
- The swap steps are in `docs/synthetic/research.md`.
