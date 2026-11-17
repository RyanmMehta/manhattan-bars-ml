# Venue-style clustering (k-means, real public data)

Data: `venue_features` ⋈ `v_bars` (1709 venues, real public data — not synthetic). Complaint targets (`noise_complaints`, `high_noise`) and lat/lon are excluded. Numeric: median-impute + standardise; categorical: one-hot (min_frequency 20). `KMeans(n_init=10, random_state=42)`.

## k sweep

| k | inertia | silhouette | smallest cluster share |
|---|---|---|---|
| 3 | 20944 | 0.165 | 21.4% |
| 4 | 18845 | 0.173 | 20.9% |
| 5 | 17372 | 0.188 | 3.7% |
| 6 | 16440 | 0.178 | 3.7% |
| 7 | 15169 | 0.186 | 0.1% |
| 8 | 14293 | 0.176 | 0.1% |

Chosen **k = 5**: highest silhouette among k with every cluster ≥ 3% of venues. Silhouettes around 0.17–0.19 mean the clusters overlap: they're useful as coarse groups, not crisp types.

## Clusters

| id | label (shown to users) | description (top features) | venues | launch venues |
|---|---|---|---|---|
| 0 | Drinks-first bar | drinks-only, rarely inspected | 364 | 0 |
| 1 | Late-night restaurant bar | web presence, late-closing, restaurant | 345 | 23 |
| 2 | Low-key local bar | no web presence, early-closing, grade A | 591 | 4 |
| 3 | Restaurant bar with outdoor seating | outdoor seating, web presence, restaurant | 63 | 4 |
| 4 | Bar & kitchen | critical violations, more violations | 346 | 4 |

Labels come from each cluster's top z-scored features and most over-represented category. They describe the public-data profile (licence, inspections, OSM, density), not quality or vibe.

Artifacts: `recs/artifacts/clusters.csv` (venue_id, cluster_id, cluster_label), `clusters.json` (profiles). Used as `cluster_label` on recommendations and as a crowd-model feature.
