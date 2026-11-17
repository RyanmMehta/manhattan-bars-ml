"""SQL for each public extract (read-only against data/manhattan_bars.db).

license_id is aliased to venue_id in every output (CONTRACTS.md v2 §D).
"""

# E1 bars.csv — v_bars LEFT JOIN venue_features (1,727 rows; 18 have no coords/features)
BARS = """
SELECT b.license_id AS venue_id, b.name, b.address, b.zip, b.neighborhood,
       b.lat, b.lon, b.venue_type, b.liquor_tier,
       f.latest_grade, b.noise_complaints, f.high_noise,
       b.density_100m, b.density_250m, f.years_licensed,
       f.osm_amenity, f.osm_closes_late
FROM v_bars b
LEFT JOIN venue_features f ON f.license_id = b.license_id
ORDER BY b.license_id
"""

# E2 venue_features_slim.csv — all venue_features rows (5,704)
VENUE_FEATURES_SLIM = """
SELECT license_id AS venue_id, venue_type, neighborhood, latest_grade, lat, lon,
       noise_complaints, high_noise, density_100m, mean_score
FROM venue_features
ORDER BY license_id
"""

# E4 context: every licensed venue (5,737) for n_venues per neighbourhood
VENUE_COUNTS = """
SELECT neighborhood, COUNT(*) AS n_venues
FROM venues
GROUP BY neighborhood
ORDER BY neighborhood
"""

# SYNTHETIC: live-sim data/live_sim.db; replaced by real `scout_reports` (backend, INCLUDE_SYNTHETIC=0)
# Demo-night reports at launch venues, accepted + pending only, reputation joined as of the report date.
LIVE_SIM_REPORTS = """
SELECT r.report_id, r.venue_id, r.scout_id, r.ts, r.crowd, r.dancing, r.line_minutes,
       r.cover_usd, r.music_genre, r.verified_presence, r.status, r.distance_m, r.is_synthetic,
       COALESCE((SELECT h.reputation FROM syn_scout_reputation_history h
                 WHERE h.scout_id = r.scout_id AND h.as_of_date <= substr(r.ts, 1, 10)
                 ORDER BY h.as_of_date DESC LIMIT 1), 0.5) AS reputation
FROM syn_scout_reports r
WHERE r.status IN ('accepted', 'pending')
  AND r.ts >= :start AND r.ts < :end
ORDER BY r.report_id
"""
