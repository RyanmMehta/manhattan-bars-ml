// All thresholds and magic numbers live here (RULES §3).

/** CONTRACTS §A: confidence >= 0.40 shows the vibe. */
export const CONF_SHOW = 0.4;
/** CONTRACTS §A: 0.20–0.39 is greyed "low confidence"; below → "No fresh reports". */
export const CONF_LOW = 0.2;
/** CONTRACTS §A: presence radius for verified_presence (server decides; client only hints). */
export const PRESENCE_RADIUS_M = 150;
/** CONTRACTS §J: freshness above this shows a "stale" tag. */
export const STALE_MIN = 60;
/** CONTRACTS §J: vibe label bands. */
export const VIBE_BANDS: ReadonlyArray<readonly [number, number, 'Chill' | 'Lively' | 'Packed']> = [
  [0, 34, 'Chill'],
  [35, 64, 'Lively'],
  [65, 100, 'Packed'],
];
// TODO(specs): refresh interval is a frontend placeholder (PRD US-02 AC6).
export const REFRESH_MS = 120_000;
export const STALE_TIME_MS = 60_000;
/** PRD US-01 AC2: LES centroid used when geolocation is unavailable. */
export const LES_CENTER = { lat: 40.7178, lon: -73.9893 } as const;
/** RULES §3: demo-login tokens are valid for 24 h. */
export const TOKEN_TTL_MS = 24 * 3600 * 1000;
/** PRD R9: if /api/health takes longer than this, offer mock mode. */
export const HEALTH_TIMEOUT_MS = 5000;
/** PRD US-03 AC1 search debounce. */
export const SEARCH_DEBOUNCE_MS = 250;
export const VENUE_PAGE_LIMIT = 50;
/** CONTRACTS §B demo moment. */
export const DEFAULT_DEMO_NOW = '2026-11-14T23:30:00-05:00';
export const COVER_OPTIONS = [0, 10, 20, 30, null] as const;
export const LINE_OPTIONS = [0, 10, 15, 30, null] as const;
export const DISTANCE_OPTIONS = [0.5, 1, 1.5, 3] as const;
export const REPORT_LINE_CHIPS = [0, 5, 10, 20, 30] as const;
