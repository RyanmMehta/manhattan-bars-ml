# Manhattan bars: database, synthetic data simulator, ML test bench

Scrapes public data on every licensed drinking venue in Manhattan, builds a
SQLite database, generates synthetic training data with three simulators, and
tests ML models trained on synthetic data against the real data.

```
./run_all.sh                 # everything (re-scrapes, ~10 min)
SKIP_SCRAPE=1 ./run_all.sh   # rebuild from the data already in data/raw/
```

## 1. Data sources (`src/scrape.py` → `data/raw/`)

| Source | What it gives | Rows (Oct 2026) |
|---|---|---|
| NY State Liquor Authority, active licenses (data.ny.gov `9s3h-dpkz`) | every licensed venue: name, address, coordinates, license class, issue date | 9,917 Manhattan licenses |
| NYC DOHMH inspections (data.cityofnewyork.us `43nn-pn8j`) | health scores, grades, violations, cuisine | 109,845 rows / 12,603 establishments |
| NYC 311 (`erm2-nwe9`), location type *Club/Bar/Restaurant*, last 3 years | noise complaints with address and coordinates | 31,190 complaints |
| OpenStreetMap (Overpass API) | bars, pubs, nightclubs, beer gardens with opening hours, outdoor seating, website | 1,523 venues (bbox) |

No API keys are needed. Yelp and Google Places have richer data (ratings,
price level), but both need a key and their terms forbid bulk scraping, so they
are left out.

## 2. Database (`src/build_db.py` → `data/manhattan_bars.db`)

| Table | Contents |
|---|---|
| `sla_licenses`, `inspections`, `complaints_311`, `osm_venues` | raw source data, flattened |
| `venues` | **5,737 on-premises drinking venues** (bars, taverns, restaurants with liquor, clubs, hotel bars, cabarets), each matched to its DOHMH establishment (`camis`), OSM node (`osm_id`) and 311 complaint count |
| `v_bars` (view) | 1,727 bars in the narrow sense: bar/tavern, club or nightlife license, or tagged bar/pub/nightclub in OSM |
| `venue_features` | ML-ready table, one row per venue (24 columns) |
| `synthetic_<method>_<n>` | synthetic rows written by `simulate.py` |

How the sources are joined:
- DOHMH: same normalised address + zip, best name match; otherwise within 60 m with a strong name match. 87% of venues matched.
- OSM: within 60 m with a name match. 70% of the OSM bars inside Manhattan matched (the rest are mostly licensed under a different legal name).
- 311: same normalised address, otherwise the nearest complaint address within 30 m with the same house number (this catches wrong ZIPs in the license data and street aliases such as Adam Clayton Powell Jr Blvd = 7th Ave). Venues sharing an address share its complaints. 32% of venues have at least one complaint.
- Duplicate licenses for the same venue (renewal or transfer both still active) are collapsed to the oldest.

Example queries:
```sql
-- noisiest bars
SELECT name, address, noise_complaints FROM v_bars ORDER BY noise_complaints DESC LIMIT 20;
-- inspection history of one venue
SELECT i.* FROM venues v JOIN inspections i ON i.camis = v.camis WHERE v.name LIKE '%Cubby%';
-- bar density by neighbourhood
SELECT neighborhood, COUNT(*) FROM venues WHERE venue_type = 'Bar/Tavern' GROUP BY 1 ORDER BY 2 DESC;
```

`venue_features` columns:
- categorical: `venue_type`, `liquor_tier`, `neighborhood`, `cuisine`, `latest_grade`, `osm_amenity`
- binary: `dohmh_matched`, `has_pest_violation`, `osm_closes_late`, `osm_outdoor_seating`, `osm_has_website`
- numeric: `lat`, `lon`, `years_licensed`, `n_additional_bars`, `density_100m`, `density_250m`, `n_inspections`, `mean_score`, `max_score`, `n_violations`, `n_critical_violations` (scores are -1 when no inspection record matched)
- targets: `noise_complaints` (3-year count), `high_noise` (≥ 3 complaints, 17.1% of venues)

## 3. Simulator (`src/synth.py`, `src/simulate.py`)

| Method | How it works |
|---|---|
| `independent` | resamples each column on its own. Baseline: correct marginals, no relationships |
| `copula` | Gaussian copula: empirical marginals plus a correlation matrix in normal-score space |
| `cart` | sequential CART synthesis (as in R's *synthpop*): each column is drawn from the leaf of a decision tree fitted on the previous columns |

```
python -I src/simulate.py --method cart --n 50000
python -I src/simulate.py --method cart --n 2000 --where "venue_type == 'Bar/Tavern' and neighborhood == 'East Village'"
```
`--where` gives conditional or what-if sampling (rejection sampling on any pandas query).
`high_noise` is always recomputed from the synthetic complaint count, so the label stays consistent with it.

## 4. Testing synthetic against real (`src/evaluate.py` → `reports/`)

The real venues are split 70/30. Generators see only the 70% training split, and
every score is measured on the 30% of real venues that no generator saw. This is
repeated over 3 seeds.

- **TRTR**: train on real, test on real (the ceiling)
- **TSTR**: train on synthetic only, test on real (can synthetic replace real?)
- **AUG**: real plus 2× synthetic, test on real (does synthetic add anything?)

Models: logistic regression, random forest, gradient boosting (classification
of `high_noise`) and a gradient-boosting regressor (log complaint count). The
report also covers fidelity (KS/TVD per column, correlation error, and a
discriminator AUC where 0.5 means real and synthetic can't be told apart) and
privacy (distance to the closest real record, and exact-copy rate).

See `reports/report.md` for the full tables.

### Results (Oct 2026 data, 3 seeds, ROC AUC on held-out real venues)

| Training data | Logistic reg. | Random forest | Grad. boosting |
|---|---|---|---|
| Real only (TRTR) | 0.723 | 0.730 | 0.723 |
| CART synthetic only | 0.704 | 0.694 | 0.679 |
| Copula synthetic only | 0.624 | 0.615 | 0.574 |
| Independent synthetic only | 0.491 | 0.504 | 0.470 |
| Real + 2× CART | 0.722 | 0.722 | 0.725 |

- **CART is the usable simulator.** Models trained only on CART data keep about 95% of the real-data AUC. The copula keeps the marginals and linear correlations but loses the non-linear structure (discriminator AUC 0.99). The independent baseline teaches nothing, as expected.
- **Synthetic data does not beat real data.** Adding CART rows to the real training set leaves AUC unchanged. A generator fitted on the same 4k venues cannot add information they don't contain. Synthetic data is useful here for sharing, prototyping, stress-testing pipelines and what-if sampling, not for raising accuracy.
- **CART rows stay close to real ones.** Its discriminator AUC is below 0.5 (0.42) because real held-out rows have near-twins among the synthetic rows. Its distance-to-closest-record ratio is 0.94, with 0.1% exact copies. Raise `min_samples_leaf` in `CARTSynth` if the synthetic set will be shared outside your team.
- F1 uses a 0.5 threshold against a 17% base rate, so it understates every model. Compare models on ROC AUC and PR AUC.
- The task is hard on its own (AUC around 0.72). Public data says little about a bar's music, crowd or neighbours, and those drive complaints.

## Caveats

- The venue universe is liquor licensees. A bar running without a license, or one with a pending license, is not in it.
- 311 counts depend on who complains (residential density, tolerance), not only on how loud a bar is. Treat the target as complaint risk.
- OSM coverage is volunteer-made. `osm_amenity = not_listed` means missing from OSM, not "not a bar".
- Beer/wine vs full-liquor tiers are inferred from license class codes.
