# OUTLINE — research build plan

Sizes: S ≈ < 1 h, M ≈ 1-3 h, L ≈ 3-6 h. Updated for CONTRACTS v2.
Deadline: all MVP deliverables pushed by **Fri Nov 13 18:00 ET** (v2 §I);
research is merged 2nd (after specs). Phase E continues after the deadline.

## 1. Ordered tasks

### Phase A — desk research (real data)
- [ ] A1 (S) Create `research/README.md`, `docs/workstreams/research.md` skeleton, `docs/synthetic/research.md` skeleton.
- [ ] A2 (M) Re-check legacy apps: BarHop, Buzzd, nYtevibe, What's Playin, BarHopper — app store listing, website, last update, press; status live/dead/pivoted/unknown.
- [ ] A3 (M) Current substitutes: Google Maps popular times/live busyness, Instagram (stories, location tags), Snap Map, TikTok, Partiful, Resy, DICE, Posh, Eventbrite, Yelp, Beli, Fever; plus group chats (qualitative).
- [ ] A4 (S) Write `research/competitors.csv` (schema §4.1); every row sourced + `retrieved_at`.
- [ ] A5 (M) `research/competitive_matrix.md`: 8+ dimensions × competitors, footnotes, gaps we fill, "why legacy apps failed" hypotheses (labelled).
- [ ] A6 (S) Positioning statement + 2×2 spec (freshness × personalization) in the matrix doc.

### Phase B — instruments
- [ ] B1 (S) `research/hypotheses.md`: H1-H12 (pain, frequency, current tools, trust, scouting motivation, operator WTP…), each with metric + threshold placeholder.
- [ ] B2 (M) `research/interview_guide/consumer.md` (25-30 min), `scout.md` (20 min), `operator.md` (25 min); each: screener, consent, warm-up, past-behavior core, concept test (mockups), wrap-up; questions tagged with H-IDs.
- [ ] B3 (S) `research/interview_guide/note_template.md` = fields of `interviews` schema; `recruiting_plan.md` (target 10-15: 7 consumers, 3 scouts, 3-5 operators; channels; schedule).
- [ ] B4 (M) `research/survey/questions.md` (≤ 22 Q, ≤ 5 min) + `research/survey/codebook.csv`.

### Phase C — synthetic data
- [ ] C1 (M) `research/gen_synthetic.py` producing the three datasets (§5) from `PRIORS`, seeded.
- [ ] C2 (S) Confirm CSV-only output (v2 §E: research `syn_` tables are not loaded into any DB); `GENRES` constant matches v2 §E list.
- [ ] C3 (M) `research/validate.py` (codebook, `is_synthetic`, venue_ids, PII scan, competitor sourcing).
- [ ] C4 (M) `research/tests/` per RULES §7.
- [ ] C5 (S) Fill `docs/synthetic/research.md` registry.

### Phase D — business model and synthesis
- [ ] D1 (M) `research/business_model.md`: tiers, placeholder prices, unit economics, falsification tests.
- [ ] D2 (S) `research/analysis.py` → `research/synthetic/summary_tables.csv` (aggregates for tableau, `is_synthetic=1`).
- [ ] D3 (M) `research/summary.md`: ≤ 10 tagged findings + hand-offs per workstream.
- [ ] D4 (S) Slide-ready bullets in `research/presentation_notes.md` for integration.

### Phase E — real data (stretch / later)
- [ ] E1 (L) Run ≥ 3 real interviews; log to `research/interviews/interviews.csv` (`is_synthetic=0`).
- [ ] E2 (M) Launch survey (Google Forms or Qualtrics); export to `research/survey/responses.csv`.
- [ ] E3 (S) Re-run analysis on real rows; re-tag findings `[REAL n=…]`.

## 2. File tree to be created
```
research/
  README.md
  competitors.csv
  competitive_matrix.md
  hypotheses.md
  business_model.md
  summary.md
  presentation_notes.md
  gen_synthetic.py
  analysis.py
  validate.py
  interview_guide/{consumer,scout,operator,note_template,recruiting_plan}.md
  survey/{questions.md,codebook.csv}
  interviews/            # real rows only (empty until E1); .gitkeep
  synthetic/
    syn_interviews.csv
    syn_interview_quotes.csv
    syn_survey_responses.csv
    summary_tables.csv
  tests/{test_generator.py,test_validate.py,test_competitors.py}
docs/workstreams/research.md
docs/synthetic/research.md
```

## 3. Interfaces

Consumed (from `docs/CONTRACTS.md`):
- `data/launch_venues.csv` — `license_id` as `venue_id`, `name` for mention lists.
- Preferences object field names (`genres`, `want_dancing`, `crowd_pref`,
  `max_cover_usd`, `max_line_minutes`, `max_distance_km`, `group_size`) — survey
  factor columns reuse these names so ml-recs/specs can map directly.
- `syn_venue_attributes.style` / `genres` vocab — survey genre options use the
  same vocabulary.
- Synthetic data rule (all 5 points).

Provided (research → others; CSV columns = SQLite columns):
- `syn_survey_responses`, `syn_interviews`, `syn_interview_quotes` (schemas §4).
- `research/synthetic/summary_tables.csv`: `metric, segment, value, n, is_synthetic`.
- `research/competitors.csv` (real).
- `research/summary.md` hand-off table.
No HTTP API endpoints; backend need not expose research data.

**Contract change requests:** all three earlier requests were resolved in
CONTRACTS v2 (research tables listed in §E, `docs/prd/<name>/` in §C, shared
genre vocabulary in §E). None open.

Shared genre vocabulary (v2 §E), used for every genre option in survey and
interview data: `hip-hop, r&b, house, techno, pop, top-40, latin, reggaeton,
afrobeats, rock, indie, jazz, soul, funk, disco, 90s-00s, edm, live-band,
karaoke, mixed`.

## 4. Schemas

### 4.1 `research/competitors.csv` (real)
`competitor_id, name, category (legacy_app|maps|social|events|reservations|reviews|other),
platform, status (live|dead|pivoted|unknown), last_seen_active (YYYY-MM or unknown),
realtime_signal (Y|partial|N), crowd_sourced, group_matching, shows_confidence,
venue_tools, nyc_coverage, reporter_incentives, consumer_price, revenue_model,
why_failed_hypothesis (nullable), source_url, retrieved_at (YYYY-MM-DD), notes`

### 4.2 `syn_interviews`
`interview_id (syn-int-### synthetic / int-r-### real), segment (consumer|scout|operator),
date, age_band (18-20|21-24|25-29|30-34|35+|na), nights_out_per_month (int),
typical_group_size (int), neighborhoods (pipe), current_tools (pipe: google_maps|instagram|
group_chat|partiful|resy|dice|yelp|tiktok|none), bad_pick_last_month (0/1),
favorite_genres (pipe, from shared vocabulary), top_factor_1..3 (genres|want_dancing|crowd_pref|max_cover_usd|max_line_minutes|
max_distance_km|price|friends_there), freshness_tolerance_min (int),
would_scout (0-3 Likert-ish: no|maybe|yes|already), scout_motivator (points|perks|status|helping|none),
operator_role (nullable), operator_wtp_usd_month (nullable), operator_wants (pipe, nullable),
venue_mentions (pipe of venue_id), concept_reaction (1-5), is_synthetic`

### 4.3 `syn_interview_quotes`
`quote_id (syn-q-#### / q-r-####), interview_id, hypothesis_id (H1..H12), theme (pain|tools|trust|scouting|pricing|other),
sentiment (-1/0/1), text (starts "[SYNTHETIC] "), is_synthetic`

### 4.4 `syn_survey_responses`
`response_id (syn-srv-#### / srv-r-####), submitted_at (ISO, ET; synthetic spread Oct 26–Nov 12 2026), age_band, student (0/1), nights_out_per_month,
typical_group_size, who_picks (me|friend|rotates|group_vote), decision_minutes (int),
current_tools (pipe), bad_pick_last_month (0/1), importance_genres … importance_price
(1-5 each, one per factor above), freshness_tolerance_min, trust_cue_pref
(n_reports|recency|verified_scout|venue_official), would_use_weekly (0/1),
would_scout (0-3), reports_per_night_if_scout (int), points_value_pref
(free_drink|skip_line|cover_waiver|status), nps_concept (0-10), is_synthetic`

## 5. Synthetic datasets

| Dataset | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `syn_interviews` (n=15: 8 consumer, 3 scout, 4 operator) | Coded notes from 10-15 semi-structured interviews | `gen_synthetic.py`: sample segment counts, then fields from `PRIORS` (e.g. nights_out ~ Poisson(λ=[6]), bad_pick ~ Bernoulli([0.6])); venue_mentions drawn from launch venues weighted by OSM-match | `research/interviews/interviews.csv` from note template (E1) | 1. Fill real CSV with same columns, `is_synthetic=0`. 2. `analysis.py --source real`. 3. Keep synthetic CSV for demos or delete it; nothing to drop from any DB. 4. Re-tag findings. |
| `syn_interview_quotes` (~4-6 per interview) | Tagged verbatim quotes | Template sentences per theme × sentiment, filled with sampled fields, prefixed `[SYNTHETIC] ` | Real quotes transcribed from notes (anonymized) | Same as above; quotes CSV in `research/interviews/quotes.csv`. |
| `syn_survey_responses` (n=300 placeholder) | Online survey export | Latent "nightlife intensity" z ~ N(0,1) drives nights_out, would_scout, would_use_weekly (logistic, coefficients in PRIORS) so correlations are plausible; importance Likerts from a Dirichlet over factors | Google Forms/Qualtrics export mapped via codebook (E2) | 1. Export CSV. 2. Rename columns to codebook. 3. `validate.py --real`. 4. Point tableau extract at real file. |
| `summary_tables.csv` | Aggregated findings | `analysis.py` over synthetic CSVs | Same script over real CSVs | Re-run with `--source real`. |

All PRIORS values are `[PLACEHOLDER]` guesses, each with `# SYNTHETIC:` naming
the survey/interview question whose real answer replaces it.

## 6. Test plan
- Unit: generator functions return the right columns, dtypes, ranges.
- Determinism: seed 42 twice → same SHA-256 per CSV; seed 43 → different.
- Contract: `is_synthetic` everywhere; files under `synthetic/`; tables `syn_`.
- Referential: all `venue_mentions` ∈ launch `license_id`s; quotes' `interview_id` ∈ interviews.
- Codebook: every survey column defined; allowed values respected.
- PII scan: no email/phone regex hits in `research/**`.
- No DB writes: `data/*.db` mtimes/hashes unchanged after running the generator.
- IDs: synthetic keys start `syn-`; genres ⊆ shared vocabulary (v2 §E).
- Competitors: all rows have `source_url` (http/https) and `retrieved_at`.
- Manual: a teammate pilots the consumer guide (≤ 30 min) and survey (≤ 5 min).

## 7. Demo script (≈ 2 min in the Nov 17 presentation; scenario time DEMO_NOW = Sat Nov 14 23:30 ET)
1. "Here's who tried this before": show matrix — legacy apps dead/unknown,
   substitutes are static or social, nobody shows confidence. (real)
2. Positioning statement + 2×2: we're the fresh + personalized corner. (real)
3. Interview guide snippet + recruiting plan; real interviews completed: N
   `[PLACEHOLDER]`.
4. Tableau "voice of customer" dashboard from `summary_tables.csv` with the
   "demo data" badge: top decision factors, freshness tolerance, % willing to scout.
5. Business model: free claimed profile → Pro $[49]/mo → offers $[1]/redemption;
   the test that would prove/kill each.
6. Close: what changes in the product when real data replaces synthetic
   (weights, half-life, badge copy) — show `docs/synthetic/research.md`.

## 8. Run commands (build phase)
```
python -I research/gen_synthetic.py --seed 42
python -I research/validate.py
python -I research/analysis.py --source synthetic
python -I -m pytest research/tests -q
```
