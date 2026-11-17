// Client against the MSW handlers in node: query building, `now`, auth, error mapping.
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ApiError, api, buildUrl, configureClient, getToken, setToken } from '../../src/api/client';
import { makeHandlers } from '../../src/mocks/handlers';
import { createDb } from '../../src/mocks/db';
import { DEFAULT_PREFS } from '../../src/state/prefsReducer';

const BASE = 'http://localhost/api';
const server = setupServer(...makeHandlers(createDb(), BASE));
let now: string | null = '2026-11-14T23:30:00-05:00';
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
  configureClient({ base: BASE, now: () => now });
});
afterEach(() => {
  server.resetHandlers();
  now = '2026-11-14T23:30:00-05:00';
});
afterAll(() => server.close());

describe('buildUrl', () => {
  it('appends now and drops empty params', () => {
    const u = new URL(buildUrl('/venues', { q: '', style: 'club', limit: 50 }));
    expect(u.searchParams.get('now')).toBe('2026-11-14T23:30:00-05:00');
    expect(u.searchParams.get('style')).toBe('club');
    expect(u.searchParams.has('q')).toBe(false);
  });
  it('omits now when the clock is unset', () => {
    now = null;
    expect(buildUrl('/bounties')).toBe(`${BASE}/bounties`);
  });
});

describe('api (mock backend)', () => {
  it('health', async () => expect((await api.health()).data).toBe('synthetic'));
  it('venues: launch_only, total, X-Data, distance sort', async () => {
    const r = await api.venues({ lat: 40.7203, lon: -73.9881 });
    expect(r.rows).toHaveLength(35);
    expect(r.total).toBe(35);
    expect(r.data).toBe('synthetic');
    const d = r.rows.map((x) => x.distance_km ?? 0);
    expect([...d].sort((a, b) => a - b)).toEqual(d);
    expect((await api.venues({ q: 'mehanata' })).rows[0]?.venue_id).toBe('0370-23-127248');
  });
  it('recommend returns ranked results with the demo hero', async () => {
    const r = await api.recommend({ ...DEFAULT_PREFS, genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4 });
    expect(r[0]?.name).toBe('Subject');
    expect(r[0]?.match_score).toBe(91);
    expect(r.filter((x) => x.excluded)).toHaveLength(3);
  });
  it('venue detail, state, heatmap, leaderboard, bounties, owner, plan', async () => {
    const d = await api.venue('0370-21-116653');
    expect(d.venue.display_name).toBe('Subject');
    expect((await api.venueState('0370-21-116653')).venue_id).toBe('0370-21-116653');
    expect(await api.heatmap(true)).toHaveLength(35);
    expect((await api.leaderboard())[0]?.rank).toBe(1);
    expect((await api.bounties())[0]?.points).toBe(50);
    const plan = await api.planNight({ ...DEFAULT_PREFS, n_stops: 3 });
    expect(plan).toHaveLength(3);
    const swapped = await api.planNight({ ...DEFAULT_PREFS, n_stops: 3, exclude_venue_ids: [plan[0]!.venue_id] });
    expect(swapped.map((s) => s.venue_id)).not.toContain(plan[0]!.venue_id);
  });
  it('writes need a token; report raises confidence and pays points', async () => {
    setToken(null);
    await expect(api.report({ venue_id: '0370-23-131873', crowd: 3, dancing: 1, line_minutes: 5 })).rejects.toMatchObject({ code: 'login_required' });
    const login = await api.demoLogin({ display_name: 'Demo Scout', role: 'scout' });
    setToken({ token: login.token, issued_at: Date.now(), role: 'scout', id: login.scout_id ?? null, display_name: 'Demo Scout' });
    const before = await api.venueState('0370-23-131873');
    const r = await api.report({ venue_id: '0370-23-131873', crowd: 3, dancing: 1, line_minutes: 5 });
    expect(r.points_pending).toBe(60);
    expect(r.status).toBe('pending');
    const after = await api.venueState('0370-23-131873');
    expect(after.confidence!).toBeGreaterThan(before.confidence!);
    expect(after.n_reports).toBe(before.n_reports + 1);
  });
  it('owner cannot report own venue; owner update requires owner token', async () => {
    const o = await api.demoLogin({ display_name: 'Demo Owner', role: 'owner', venue_id: '0370-23-127248' });
    setToken({ token: o.token, issued_at: Date.now(), role: 'owner', id: o.user_id ?? null, display_name: 'Demo Owner' });
    await expect(api.report({ venue_id: '0370-23-127248', crowd: 3, dancing: 1, line_minutes: 5 })).rejects.toMatchObject({ status: 403 });
    expect((await api.ownerDashboard('0370-23-127248')).demand_by_hour.length).toBeGreaterThan(5);
    await expect(api.ownerDashboard('0370-21-116653')).rejects.toMatchObject({ status: 403 });
    await api.ownerUpdate('0370-23-127248', { cover_usd: 10, dj: 'Balkan Beat', genres: ['throwbacks'], event: null, offer: '$10 before midnight', offer_expires_at: '2026-11-15T00:00:00-05:00' });
    expect((await api.venue('0370-23-127248')).offers[0]?.offer).toBe('$10 before midnight');
  });
  it('maps the error envelope and network errors', async () => {
    server.use(http.get(`${BASE}/bounties`, () => HttpResponse.json({ error: { code: 'boom', message: 'Nope', details: 1 } }, { status: 500 })));
    await expect(api.bounties()).rejects.toMatchObject({ code: 'boom', message: 'Nope', status: 500 });
    server.use(http.get(`${BASE}/scouts/leaderboard`, () => HttpResponse.error()));
    await expect(api.leaderboard()).rejects.toMatchObject({ code: 'network' });
    server.use(http.get(`${BASE}/heatmap`, () => HttpResponse.json({ not: 'a list' })));
    await expect(api.heatmap()).rejects.toBeInstanceOf(ApiError);
  });
  it('token expires after 24 h', () => {
    setToken({ token: 't', issued_at: 0, role: 'user', id: null, display_name: 'x' });
    expect(getToken(24 * 3600e3 + 1)).toBeNull();
    expect(getToken(1000)?.token).toBe('t');
  });
});
