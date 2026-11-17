// Wire types. Field names mirror docs/CONTRACTS.md exactly (snake_case). §F/§G shapes.

export type Synthetic = boolean | 0 | 1;
export type Display = 'show' | 'low' | 'none';
export type Trend = 'rising' | 'steady' | 'falling' | null;
export type Role = 'user' | 'scout' | 'owner';

export interface Preferences {
  genres: string[];
  want_dancing: boolean;
  crowd_pref: number;
  max_cover_usd: number | null;
  max_line_minutes: number | null;
  max_distance_km: number;
  lat: number;
  lon: number;
  group_size: number;
  start_time?: string;
  dwell_minutes?: number;
  max_total_walk_minutes?: number;
  exclude_venue_ids?: string[];
}

export interface LiveVenueState {
  venue_id: string;
  crowd: number | null;
  dancing: number | null;
  line_minutes: number | null;
  cover_usd: number | null;
  music_genres: string[] | null;
  vibe_score: number | null;
  confidence: number | null;
  freshness_minutes: number | null;
  n_reports: number;
  trend: Trend;
  sources: string[];
  display?: Display;
  predicted_crowd?: number | null;
  predicted_source?: string | null;
  is_synthetic: Synthetic;
}

/** CONTRACTS §J CR-19: complaint_risk object. Shown as label + level only, never as a vibe signal. */
export interface ComplaintRisk {
  label: string;
  noise_complaints_3y: number | null;
  level: 'low' | 'medium' | 'high' | null;
  score: number | null;
}

export interface VenueCard {
  venue_id: string;
  name: string;
  display_name: string | null;
  style: string | null;
  genres: string[];
  price_level: number | null;
  typical_cover_usd: number | null;
  lat: number;
  lon: number;
  distance_km?: number | null;
  opening_hours: string | null;
  is_claimed: boolean | 0 | 1;
  state: LiveVenueState | null;
  complaint_risk: ComplaintRisk | null;
  address?: string | null;
  is_synthetic: Synthetic;
}

export interface ScoutReport {
  report_id: string;
  venue_id: string;
  scout_id?: string;
  scout_level?: number | null;
  scout_display_name?: string | null;
  reputation?: number | null;
  ts: string;
  crowd: number;
  dancing: number;
  line_minutes: number;
  cover_usd: number | null;
  music_genre: string | null;
  verified_presence?: 0 | 1 | boolean;
  status?: string;
  is_synthetic: Synthetic;
}

export interface VenueUpdate {
  update_id?: string;
  venue_id: string;
  ts?: string;
  cover_usd: number | null;
  dj: string | null;
  genres: string | string[] | null;
  event: string | null;
  offer: string | null;
  offer_expires_at: string | null;
  is_synthetic?: Synthetic;
}

export interface VenueDetail {
  venue: VenueCard;
  state: LiveVenueState | null;
  recent_reports: ScoutReport[];
  offers: VenueUpdate[];
  is_synthetic?: Synthetic;
}

export interface Recommendation {
  venue_id: string;
  name: string;
  display_name?: string | null;
  match_score: number;
  vibe_score: number | null;
  confidence: number | null;
  distance_km: number | null;
  reasons: string[];
  missing: string[];
  excluded: boolean;
  excluded_reason?: string | null;
  rank_score?: number;
  rank?: number;
  cluster_label?: string | null;
  complaint_risk?: ComplaintRisk | null;
  freshness_minutes?: number | null;
  n_reports?: number | null;
  display?: Display;
  is_synthetic: Synthetic;
}

export interface PlanStop {
  order: number;
  venue_id: string;
  name: string;
  lat: number;
  lon: number;
  arrive_at: string;
  leave_at: string;
  walk_minutes_from_prev: number | null;
  distance_km: number | null;
  expected_vibe: number | null;
  match_score: number;
  confidence: number | null;
  reasons: string[];
  is_synthetic?: Synthetic;
}

export interface ReportInput {
  venue_id: string;
  crowd: number;
  dancing: number;
  line_minutes: number;
  cover_usd?: number | null;
  music_genre?: string | null;
  lat?: number;
  lon?: number;
}
export interface ReportResult {
  report_id: string;
  ts: string;
  status: 'pending' | 'accepted' | 'flagged' | 'disputed' | 'removed' | string;
  points_pending: number;
  is_synthetic?: Synthetic;
}

export interface LeaderboardRow {
  rank: number;
  scout_id: string;
  display_name: string;
  level: number;
  points: number;
  points_week: number;
  reputation: number;
  is_synthetic: Synthetic;
}

export interface Bounty {
  bounty_id: string;
  venue_id: string;
  venue_name: string;
  created_at: string;
  expires_at: string | null;
  points: number;
  reason: string;
  claimed_by: string | null;
  claimed_at?: string | null;
  is_synthetic: Synthetic;
}

export interface OwnerDashboard {
  venue_id: string;
  views: number;
  taps: number;
  saves: number;
  reports_tonight: number;
  rec_appearances: number;
  demand_by_hour: { hour: number; value: number }[];
  is_synthetic: Synthetic;
}

export interface HeatPoint {
  venue_id: string;
  lat: number;
  lon: number;
  hour?: number;
  vibe_score: number | null;
  confidence: number | null;
  n_reports: number;
  is_synthetic: Synthetic;
}

export interface Health {
  ok: boolean;
  recs?: 'real' | 'stub';
  data?: 'synthetic' | 'real' | 'mixed';
  demo_now?: string | null;
}

export interface DemoLoginInput {
  display_name: string;
  role: Role;
  venue_id?: string;
}
export interface DemoLoginResult {
  token: string;
  user_id?: string;
  scout_id?: string;
}

export interface FeedbackInput {
  user_id?: string;
  venue_id: string;
  visited: 0 | 1;
  rating: number | null;
}

export type DataHeader = 'synthetic' | 'real' | 'mixed' | null;
