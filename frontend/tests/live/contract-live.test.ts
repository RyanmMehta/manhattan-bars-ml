// T16: `npm run contract:live` — hits a real backend's /api/* and validates every response with the
// same type guards the app uses (src/api/adapters.ts). CONTRACT_BASE=http://localhost:8000/api (default).
// CONTRACT_BASE=selftest runs the same checks against the MSW mock handlers (proves the checker works).
import { setupServer } from 'msw/node';
import * as g from '../../src/api/adapters';
import { makeHandlers } from '../../src/mocks/handlers';
import { createDb } from '../../src/mocks/db';

const RAW = process.env.CONTRACT_BASE ?? 'http://localhost:8000/api';
const SELF = RAW === 'selftest';
const BASE = SELF ? 'http://contract.test/api' : RAW.replace(/\/$/, '');
const NOW = '2026-11-14T23:30:00-05:00';
const PREFS = { genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, max_cover_usd: 20, max_line_minutes: 15, max_distance_km: 1.5, lat: 40.7203, lon: -73.9881, group_size: 4 };
const server = SELF ? setupServer(...makeHandlers(createDb(), BASE)) : null;

beforeAll(() => server?.listen({ onUnhandledRequest: 'bypass' }));
afterAll(() => server?.close());

async function get(path: string) {
  const sep = path.includes('?') ? '&' : '?';
  const res = await fetch(`${BASE}${path}${sep}now=${encodeURIComponent(NOW)}`);
  return { res, json: (await res.json()) as unknown };
}
async function post(path: string, body: unknown, token?: string) {
  const res = await fetch(`${BASE}${path}?now=${encodeURIComponent(NOW)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  return { res, json: (await res.json()) as unknown };
}
const list = (v: unknown, guard: (x: unknown) => boolean) => Array.isArray(v) && v.length > 0 && v.every(guard);
const syn = (v: unknown) => typeof v === 'object' && v !== null && 'is_synthetic' in v;

describe(`contract:live against ${SELF ? 'mock self-test' : BASE}`, () => {
  let venueId = '';
  it('GET /health', async () => {
    const { json } = await get('/health');
    expect(g.isHealth(json)).toBe(true);
  });
  it('GET /venues (card shape, X-Total-Count, X-Data, is_synthetic)', async () => {
    const { res, json } = await get('/venues?launch_only=true&limit=50&lat=40.7203&lon=-73.9881');
    expect(list(json, g.isVenueCard)).toBe(true);
    expect(res.headers.get('X-Total-Count')).not.toBeNull();
    expect(['synthetic', 'real', 'mixed']).toContain(res.headers.get('X-Data'));
    const rows = json as { venue_id: string; distance_km?: number }[];
    expect(rows.every(syn)).toBe(true);
    // CONTRACTS §J CR-19: complaint_risk is an object with the fixed label.
    expect(rows.every((r) => { const c = (r as { complaint_risk?: { label?: string } | null }).complaint_risk; return c === null || c?.label === '311 noise-complaint risk'; })).toBe(true);
    expect(rows[0]?.distance_km).toBeTypeOf('number');
    venueId = rows[0]!.venue_id;
  });
  it('GET /venues/{id} and /state', async () => {
    expect(g.isVenueDetail((await get(`/venues/${venueId}`)).json)).toBe(true);
    expect(g.isLiveState((await get(`/venues/${venueId}/state`)).json)).toBe(true);
  });
  it('POST /recommend (rank, excluded_reason)', async () => {
    const { json } = await post('/recommend', PREFS);
    expect(list(json, g.isRecommendation)).toBe(true);
    expect((json as { rank?: number }[])[0]?.rank).toBe(1);
  });
  it('POST /plan-night', async () => {
    expect(list((await post('/plan-night', { ...PREFS, n_stops: 3 })).json, g.isPlanStop)).toBe(true);
  });
  it('GET /scouts/leaderboard, /bounties, /heatmap', async () => {
    expect(list((await get('/scouts/leaderboard')).json, g.isLeaderboardRow)).toBe(true);
    const b = (await get('/bounties')).json;
    expect(Array.isArray(b) && b.every(g.isBounty)).toBe(true);
    expect(list((await get('/heatmap?by=hour')).json, g.isHeatPoint)).toBe(true);
  });
  it('GET /owner/{id}/dashboard (owner bearer required)', async () => {
    expect((await get(`/owner/${venueId}/dashboard`)).res.status).toBe(401);
    const o = await post('/auth/demo-login', { display_name: 'Contract Owner', role: 'owner', venue_id: venueId });
    const tok = (o.json as { token: string }).token;
    const res = await fetch(`${BASE}/owner/${venueId}/dashboard?now=${encodeURIComponent(NOW)}`, { headers: { Authorization: `Bearer ${tok}` } });
    expect(g.isOwnerDashboard(await res.json())).toBe(true);
  });
  it('auth + writes: demo-login, reports, owner update, feedback; 401 envelope', async () => {
    const anon = await post('/reports', { venue_id: venueId, crowd: 3, dancing: 1, line_minutes: 5 });
    expect(anon.res.status).toBe(401);
    expect(g.asErrorEnvelope(anon.json)).not.toBeNull();
    const s = await post('/auth/demo-login', { display_name: 'Contract Scout', role: 'scout' });
    expect(g.isDemoLogin(s.json)).toBe(true);
    const tok = (s.json as { token: string }).token;
    const r = await post('/reports', { venue_id: venueId, crowd: 3, dancing: 1, line_minutes: 5 }, tok);
    expect(g.isReportResult(r.json)).toBe(true);
    const bad = await post('/reports', { venue_id: venueId }, tok);
    expect(bad.res.status).toBe(422);
    expect(g.asErrorEnvelope(bad.json)).not.toBeNull();
    expect((await post('/feedback', { venue_id: venueId, visited: 1, rating: 4 }, tok)).res.status).toBe(403); // scouts can't
    const usr = await post('/auth/demo-login', { display_name: 'Contract User', role: 'user' });
    const f = await post('/feedback', { venue_id: venueId, visited: 1, rating: 4 }, (usr.json as { token: string }).token);
    expect(f.res.ok).toBe(true);
    const o = await post('/auth/demo-login', { display_name: 'Contract Owner', role: 'owner', venue_id: venueId });
    const ot = (o.json as { token: string }).token;
    const u = await post(`/owner/${venueId}/updates`, { cover_usd: 10, dj: null, genres: ['house'], event: null, offer: 'test', offer_expires_at: null }, ot);
    expect(u.res.ok).toBe(true);
  });
  it.skipIf(SELF)('GET /openapi.json is published', async () => {
    const res = await fetch(`${BASE.replace(/\/api$/, '')}/openapi.json`);
    expect(res.ok).toBe(true);
  });
});
