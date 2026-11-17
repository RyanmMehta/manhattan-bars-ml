// SYNTHETIC: MSW handlers for all 14 endpoints (CONTRACTS table + §G). They serve
// precomputed fixtures (no scoring logic). Real source: the FastAPI backend in backend/.
import { http, HttpResponse, type PathParams } from 'msw';
import type * as T from '../api/types';
import { createDb, type Db, type SnapState } from './db';

const DEMO_NOW = '2026-11-14T23:30:00-05:00';
const H = { 'X-Data': 'synthetic' };
const ms = (s: string) => Date.parse(s);
const round = (x: number, d = 2) => Math.round(x * 10 ** d) / 10 ** d;

function haversineKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const R = 6371, r = (d: number) => (d * Math.PI) / 180;
  const h = Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lon - a.lon) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function iso(t: number) {
  return `${new Date(t - 5 * 3600e3).toISOString().slice(0, 19)}-05:00`;
}
function err(status: number, code: string, message: string, details: unknown = null) {
  return HttpResponse.json({ error: { code, message, details } }, { status });
}

export function makeHandlers(db: Db = createDb(), base = '/api') {
  const nowOf = (req: Request) => new URL(req.url).searchParams.get('now') ?? DEMO_NOW;
  const snapIndex = (now: string) => {
    const ts = [...new Set(db.states.map((s) => s.snapshot_ts))];
    let best = 0;
    ts.forEach((t, i) => {
      if (Math.abs(ms(t) - ms(now)) < Math.abs(ms(ts[best] ?? t) - ms(now))) best = i;
    });
    return { ts: ts[best] ?? DEMO_NOW, idx: best };
  };
  const stateOf = (id: string, now: string): T.LiveVenueState | null => {
    const { ts } = snapIndex(now);
    const s = db.states.find((x) => x.venue_id === id && x.snapshot_ts === ts);
    if (!s) return null;
    const { snapshot_ts: _s, ...rest } = s;
    void _s;
    return rest;
  };
  const card = (v: Db['venues'][number], now: string, from?: { lat: number; lon: number }): T.VenueCard => {
    const { has_dance_floor: _d, capacity: _c, ...rest } = v;
    void _d; void _c;
    return {
      ...rest,
      distance_km: from ? round(haversineKm(from, v), 2) : null,
      state: stateOf(v.venue_id, now),
    };
  };
  const auth = (req: Request) => {
    const h = req.headers.get('Authorization');
    const tok = h?.startsWith('Bearer ') ? h.slice(7) : null;
    return tok ? db.tokens.get(tok) ?? null : null;
  };
  const presetFor = (p: Partial<T.Preferences>) => {
    // Pick the fixture preset closest to the request (genre overlap, dancing, crowd).
    let best = 'hip-hop-dancers', bestScore = -Infinity;
    for (const [k, v] of Object.entries(db.presets)) {
      const g = (p.genres ?? []).filter((x) => v.genres.includes(x)).length;
      const s = g * 3 + (v.want_dancing === !!p.want_dancing ? 1 : 0) - Math.abs((p.crowd_pref ?? 3) - v.crowd_pref) * 0.5 - (v.genres.length && !(p.genres ?? []).length ? 2 : 0);
      if (s > bestScore) { bestScore = s; best = k; }
    }
    return best;
  };
  const recsFor = (p: Partial<T.Preferences>, now: string) => {
    const snaps = db.recs[presetFor(p)] ?? [];
    const { idx } = snapIndex(now);
    const snap = snaps[idx] ?? snaps[0];
    if (!snap) return [];
    return snap.results.map((r) => {
      const s = stateOf(r.venue_id, now);
      return s ? { ...r, vibe_score: s.vibe_score, confidence: s.confidence, freshness_minutes: s.freshness_minutes, display: s.display, n_reports: s.n_reports } : r;
    });
  };
  const p = (path: string) => `${base}${path}`;

  return [
    http.get(p('/health'), () => HttpResponse.json({ ok: true, recs: 'stub', data: 'synthetic', demo_now: DEMO_NOW })),

    http.post(p('/auth/demo-login'), async ({ request }) => {
      const b = (await request.json()) as Partial<T.DemoLoginInput>;
      if (!b.display_name || !b.role) return err(422, 'validation_error', 'display_name and role are required');
      const token = `syn-token-${db.seq++}`;
      const id = b.role === 'scout' ? 'syn-s-demo' : `syn-u-${String(db.seq).padStart(4, '0')}`;
      db.tokens.set(token, { role: b.role, id, venue_id: b.venue_id });
      return HttpResponse.json(b.role === 'scout' ? { token, scout_id: id } : { token, user_id: id });
    }),

    http.get(p('/venues'), ({ request }) => {
      const u = new URL(request.url).searchParams;
      const now = nowOf(request);
      const q = (u.get('q') ?? '').toLowerCase();
      const style = u.get('style');
      const genre = u.get('genre');
      const lat = u.get('lat'), lon = u.get('lon');
      const from = lat && lon ? { lat: Number(lat), lon: Number(lon) } : undefined;
      let rows = db.venues
        .filter((v) => !q || v.display_name?.toLowerCase().includes(q) || v.name.toLowerCase().includes(q) || v.address.toLowerCase().includes(q))
        .filter((v) => !style || v.style === style)
        .filter((v) => !genre || v.genres.includes(genre))
        .map((v) => card(v, now, from));
      if (from) rows = rows.sort((a, b) => (a.distance_km ?? 0) - (b.distance_km ?? 0));
      const limit = Math.min(200, Number(u.get('limit') ?? 50));
      const offset = Number(u.get('offset') ?? 0);
      return HttpResponse.json(rows.slice(offset, offset + limit), { headers: { ...H, 'X-Total-Count': String(rows.length) } });
    }),

    http.get(p('/venues/:id/state'), ({ request, params }) => {
      const s = stateOf(String(params.id), nowOf(request));
      return s ? HttpResponse.json(s) : err(404, 'not_found', 'Venue not found');
    }),

    http.get<PathParams>(p('/venues/:id'), ({ request, params }) => {
      const now = nowOf(request);
      const v = db.venues.find((x) => x.venue_id === params.id);
      if (!v) return err(404, 'not_found', 'Venue not found');
      const recent = db.reports
        .filter((r) => r.venue_id === v.venue_id && ms(r.ts) <= ms(now) + 120e3 && ms(now) - ms(r.ts) <= 180 * 60e3)
        .sort((a, b) => ms(b.ts) - ms(a.ts))
        .slice(0, 6);
      const offers = db.updates.filter((x) => x.venue_id === v.venue_id && (!x.offer_expires_at || ms(x.offer_expires_at) > ms(now)));
      return HttpResponse.json({ venue: card(v, now), state: stateOf(v.venue_id, now), recent_reports: recent, offers, is_synthetic: 1 });
    }),

    http.post(p('/reports'), async ({ request }) => {
      const who = auth(request);
      if (!who) return err(401, 'unauthorized', 'Bearer token required');
      const b = (await request.json()) as Partial<T.ReportInput>;
      if (!b.venue_id || b.crowd === undefined || b.dancing === undefined || b.line_minutes === undefined) {
        return err(422, 'validation_error', 'venue_id, crowd, dancing and line_minutes are required', { fields: ['venue_id', 'crowd', 'dancing', 'line_minutes'] });
      }
      if (who.role === 'owner' && who.venue_id === b.venue_id) return err(403, 'forbidden', 'Owners cannot report their own venue');
      const v = db.venues.find((x) => x.venue_id === b.venue_id);
      if (!v) return err(404, 'not_found', 'Venue not found');
      const now = nowOf(request);
      const dist = b.lat !== undefined && b.lon !== undefined ? haversineKm({ lat: b.lat, lon: b.lon }, v) * 1000 : null;
      const id = `syn-r-m${String(db.seq++).padStart(5, '0')}`;
      db.reports.push({
        report_id: id, venue_id: v.venue_id, scout_id: who.id, scout_level: 1, ts: now,
        crowd: b.crowd, dancing: b.dancing, line_minutes: b.line_minutes,
        cover_usd: b.cover_usd ?? null, music_genre: b.music_genre ?? null,
        verified_presence: dist !== null && dist <= 150 ? 1 : 0, status: 'pending', is_synthetic: 1,
      });
      // Fixed demo step (OUTLINE §4): this venue's n_reports +1, confidence +0.25 from `now` on.
      const { idx } = snapIndex(now);
      const tsList = [...new Set(db.states.map((s) => s.snapshot_ts))];
      db.states.forEach((s: SnapState) => {
        if (s.venue_id !== v.venue_id || tsList.indexOf(s.snapshot_ts) < idx) return;
        s.n_reports += 1;
        s.confidence = round(Math.min(0.95, (s.confidence ?? 0) + 0.25));
        s.freshness_minutes = 0;
        s.crowd = s.crowd ?? b.crowd ?? null;
        s.dancing = s.dancing ?? b.dancing ?? null;
        s.line_minutes = b.line_minutes ?? s.line_minutes;
        if (b.cover_usd !== undefined && b.cover_usd !== null) s.cover_usd = b.cover_usd;
        if (s.vibe_score === null) s.vibe_score = Math.round(((b.crowd ?? 3) - 1) * 20 + (b.dancing ?? 0) * 5);
        s.display = s.confidence >= 0.4 ? 'show' : s.confidence >= 0.2 ? 'low' : 'none';
      });
      const bounty = db.bounties.find((x) => x.venue_id === v.venue_id && !x.claimed_by);
      const pts = 10 + (bounty?.points ?? 0);
      if (bounty) { bounty.claimed_by = who.id; bounty.claimed_at = now; }
      const scout = db.scouts.find((s) => s.scout_id === who.id);
      if (scout) { scout.points += pts; scout.points_week += pts; }
      if (db.owner[v.venue_id]) db.owner[v.venue_id]!.reports_tonight += 1;
      return HttpResponse.json({ report_id: id, ts: now, status: 'pending', points_pending: pts, is_synthetic: 1 }, { status: 201 });
    }),

    http.post(p('/recommend'), async ({ request }) => {
      const b = (await request.json()) as Partial<T.Preferences>;
      return HttpResponse.json(recsFor(b, nowOf(request)), { headers: H });
    }),

    http.post(p('/plan-night'), async ({ request }) => {
      const b = (await request.json()) as Partial<T.Preferences> & { n_stops?: number };
      const now = nowOf(request);
      const n = Math.min(4, Math.max(2, b.n_stops ?? 3));
      const dwell = b.dwell_minutes ?? 60;
      const excl = new Set(b.exclude_venue_ids ?? []);
      const pool = recsFor(b, now).filter((r) => !r.excluded && !excl.has(r.venue_id));
      // SYNTHETIC: greedy nearby chain over fixture results; real source recs.routing.plan_night.
      const stops: T.PlanStop[] = [];
      let t = ms(b.start_time ?? now);
      let prev: { lat: number; lon: number } | null = null;
      const used = new Set<string>();
      while (stops.length < n) {
        const cand = pool
          .filter((r) => !used.has(r.venue_id))
          .map((r) => ({ r, v: db.venues.find((x) => x.venue_id === r.venue_id)! }))
          .sort((a, c) => (prev ? haversineKm(prev, a.v) - haversineKm(prev, c.v) : 0) * 30 - (a.r.match_score - c.r.match_score))[0];
        if (!cand) break;
        used.add(cand.r.venue_id);
        const km = prev ? haversineKm(prev, cand.v) : null;
        const walk = km === null ? null : Math.max(1, Math.round((km / 5) * 60));
        t += (walk ?? 0) * 60e3;
        stops.push({
          order: stops.length + 1, venue_id: cand.r.venue_id, name: cand.r.name, lat: cand.v.lat, lon: cand.v.lon,
          arrive_at: iso(t), leave_at: iso(t + dwell * 60e3), walk_minutes_from_prev: walk,
          distance_km: km === null ? null : round(km), expected_vibe: cand.r.vibe_score,
          match_score: cand.r.match_score, confidence: cand.r.confidence, reasons: cand.r.reasons.slice(0, 2), is_synthetic: 1,
        });
        t += dwell * 60e3;
        prev = cand.v;
      }
      return HttpResponse.json(stops, { headers: H });
    }),

    http.post(p('/feedback'), async ({ request }) => {
      if (!auth(request)) return err(401, 'unauthorized', 'Bearer token required');
      const b = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ feedback_id: `syn-f-${db.seq++}`, ...b, is_synthetic: 1 }, { status: 201 });
    }),

    http.get(p('/scouts/leaderboard'), () => {
      const rows = [...db.scouts].sort((a, b) => b.points - a.points).map((s, i) => ({ rank: i + 1, ...s }));
      return HttpResponse.json(rows, { headers: H });
    }),

    http.get(p('/bounties'), ({ request }) => {
      const now = nowOf(request);
      const rows = db.bounties.filter((b) => !b.claimed_by && (!b.expires_at || ms(b.expires_at) > ms(now)) && ms(b.created_at) <= ms(now) + 3 * 3600e3);
      return HttpResponse.json(rows, { headers: H });
    }),

    http.get(p('/owner/:id/dashboard'), ({ params }) => {
      const d = db.owner[String(params.id)];
      return d ? HttpResponse.json(d) : err(404, 'not_found', 'Venue not found');
    }),

    http.post(p('/owner/:id/updates'), async ({ request, params }) => {
      const who = auth(request);
      if (!who) return err(401, 'unauthorized', 'Bearer token required');
      if (who.role !== 'owner' || who.venue_id !== params.id) return err(403, 'forbidden', 'Log in as this venue’s owner');
      const b = (await request.json()) as Omit<T.VenueUpdate, 'venue_id'>;
      const u: T.VenueUpdate = { ...b, update_id: `syn-u-${db.seq++}`, venue_id: String(params.id), ts: nowOf(request), is_synthetic: 1 };
      db.updates.push(u);
      return HttpResponse.json(u, { status: 201 });
    }),

    http.get(p('/heatmap'), ({ request }) => {
      const now = nowOf(request);
      const byHour = new URL(request.url).searchParams.get('by') === 'hour';
      const rows = db.venues.map((v) => {
        const s = stateOf(v.venue_id, now);
        return {
          venue_id: v.venue_id, lat: v.lat, lon: v.lon,
          ...(byHour ? { hour: new Date(ms(now) - 5 * 3600e3).getUTCHours() } : {}),
          vibe_score: s?.vibe_score ?? null, confidence: s?.confidence ?? null, n_reports: s?.n_reports ?? 0, is_synthetic: 1,
        };
      });
      return HttpResponse.json(rows, { headers: H });
    }),
  ];
}
