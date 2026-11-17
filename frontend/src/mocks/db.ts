// SYNTHETIC: in-memory mock database over the syn_* fixtures. Replaced by the backend
// (/api/*) in live mode; delete src/mocks/ once VITE_API_MODE=live is the only mode.
import venuesFx from './fixtures/synthetic/syn_venues.json';
import statesFx from './fixtures/synthetic/syn_states.json';
import reportsFx from './fixtures/synthetic/syn_reports.json';
import boardFx from './fixtures/synthetic/syn_leaderboard.json';
import bountiesFx from './fixtures/synthetic/syn_bounties.json';
import ownerFx from './fixtures/synthetic/syn_owner_dashboard.json';
import recsFx from './fixtures/synthetic/syn_recommendations.json';
import type * as T from '../api/types';

export type SnapState = T.LiveVenueState & { snapshot_ts: string };
type VenueRow = Omit<T.VenueCard, 'state' | 'distance_km'> & { has_dance_floor: number; capacity: number; address: string };
type Scout = Omit<T.LeaderboardRow, 'rank'>;
type RecSnap = { snapshot_ts: string; results: T.Recommendation[] };

const clone = <X,>(x: X): X => JSON.parse(JSON.stringify(x)) as X;

export function createDb() {
  return {
    venues: clone(venuesFx.rows) as VenueRow[],
    states: clone(statesFx.rows) as SnapState[],
    reports: clone(reportsFx.rows) as T.ScoutReport[],
    scouts: clone(boardFx.rows) as Scout[],
    bounties: clone(bountiesFx.rows) as T.Bounty[],
    owner: clone(ownerFx.rows) as Record<string, T.OwnerDashboard>,
    recs: clone(recsFx.rows) as unknown as Record<string, RecSnap[]>,
    presets: recsFx.presets as Record<string, { genres: string[]; want_dancing: boolean; crowd_pref: number }>,
    updates: [] as T.VenueUpdate[],
    tokens: new Map<string, { role: T.Role; id: string; venue_id?: string }>(),
    seq: 1,
  };
}
export type Db = ReturnType<typeof createDb>;
