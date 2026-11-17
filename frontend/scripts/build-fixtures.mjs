// SYNTHETIC: builds the frontend mock-API fixtures. Real source that replaces them:
// the backend /api/* endpoints (recs.live_state / recs.scoring / recs.routing over live_sim.db
// and, later, real scout_reports / venue_updates / venue_events tables).
//
// Inputs (read-only): ../data/launch_venues.csv (real public data: name, address, lat, lon,
// noise_complaints) and ../data/synthetic_live/*.csv when live-sim has produced them.
// If the live-sim CSVs are missing, values come from a seeded generator (seed 42).
// Output: src/mocks/fixtures/synthetic/syn_*.json. Every row carries is_synthetic: 1.
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const out = join(here, '..', 'src', 'mocks', 'fixtures', 'synthetic');
mkdirSync(out, { recursive: true });

// ---------- helpers ----------
function parseCsv(text) {
  const rows = [];
  let row = [], field = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') q = false;
      else field += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ''])));
}
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(42);
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const round = (x, d = 0) => Math.round(x * 10 ** d) / 10 ** d;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
function haversineKm(a, b) {
  const R = 6371, toR = (d) => (d * Math.PI) / 180;
  const dLat = toR(b.lat - a.lat), dLon = toR(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a.lat)) * Math.cos(toR(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function cleanName(n) {
  const s = n.replace(/\s+/g, ' ').replace(/\b(LLC|INC|CORP)\b\.?/gi, '').trim();
  if (s === s.toUpperCase()) return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/'S\b/g, "'s");
  return s;
}
const iso = (d) => {
  // America/New_York on Nov 14-15 2026 is EST (-05:00)
  const t = new Date(d.getTime() - 5 * 3600e3);
  return t.toISOString().slice(0, 19) + '-05:00';
};

const GENRES = ['hip-hop', 'r&b', 'afrobeats', 'latin', 'reggaeton', 'house', 'techno', 'edm', 'disco', 'pop', 'top-40', 'throwbacks', 'indie', 'rock', 'punk', 'jazz', 'soul-funk'];
const LABEL = { 'hip-hop': 'Hip-hop', 'r&b': 'R&B', edm: 'EDM', 'top-40': 'Top 40', 'soul-funk': 'Soul/funk' };
const label = (g) => LABEL[g] ?? g[0].toUpperCase() + g.slice(1);
const STYLES = ['dive', 'cocktail', 'club', 'lounge', 'pub', 'restaurant-bar'];
// Hand-set attributes so the OUTLINE §7 demo script has a story. SYNTHETIC.
const OVERRIDES = {
  '0370-21-116653': { display_name: 'Subject', genres: ['hip-hop', 'r&b'], style: 'lounge', has_dance_floor: 1, typical_cover_usd: null, price_level: 2 },
  '0370-24-136564': { display_name: 'The Box', genres: ['hip-hop', 'house'], style: 'club', has_dance_floor: 1, typical_cover_usd: 40, price_level: 4 },
  '0370-23-127248': { display_name: 'Mehanata Bulgarian Bar', genres: ['throwbacks', 'pop'], style: 'club', has_dance_floor: 1, typical_cover_usd: 10, price_level: 2, is_claimed: 1 },
  '0370-23-131873': { display_name: 'Clockwork Bar', genres: ['rock', 'punk'], style: 'dive', has_dance_floor: 0, typical_cover_usd: 0, price_level: 1 },
  '0370-24-130236': { display_name: 'Treasure Club International', genres: ['hip-hop', 'afrobeats', 'r&b'], style: 'club', has_dance_floor: 1, typical_cover_usd: 20, price_level: 3 },
  '0370-24-138636': { display_name: 'Attaboy', genres: ['jazz', 'soul-funk'], style: 'cocktail', has_dance_floor: 0, typical_cover_usd: 0, price_level: 3 },
  '0370-24-124394': { display_name: 'Apt 5' },
  '0370-24-136682': { display_name: 'Baby Grand LES' },
  '0370-24-119240': { display_name: 'Home Sweet Home' },
  '0267-22-114328': { display_name: 'Skin Contact' },
};

// ---------- venues ----------
const launch = parseCsv(readFileSync(join(root, 'data', 'launch_venues.csv'), 'utf8'));
const maxNoise = Math.max(...launch.map((v) => Number(v.noise_complaints) || 0));
const liveDir = join(root, 'data', 'synthetic_live');
const attrCsv = join(liveDir, 'syn_venue_attributes.csv');
const liveAttrs = existsSync(attrCsv) ? Object.fromEntries(parseCsv(readFileSync(attrCsv, 'utf8')).map((r) => [r.venue_id, r])) : {};
const usingLiveSim = Object.keys(liveAttrs).length > 0;

const venues = launch.map((v) => {
  const o = OVERRIDES[v.license_id] ?? {};
  const la = liveAttrs[v.license_id];
  const nG = 1 + Math.floor(rnd() * 3);
  const genres = la ? la.genres.split('|') : o.genres ?? [...new Set(Array.from({ length: nG }, () => pick(GENRES)))];
  const style = la?.style ?? o.style ?? pick(STYLES);
  const dance = la ? Number(la.has_dance_floor) : o.has_dance_floor ?? (style === 'club' || rnd() < 0.2 ? 1 : 0);
  const price = la ? Number(la.price_level) : o.price_level ?? 1 + Math.floor(rnd() * 4);
  const cover = la ? (la.typical_cover_usd === '' ? null : Number(la.typical_cover_usd)) : 'typical_cover_usd' in o ? o.typical_cover_usd : pick([0, 0, 0, 5, 10, 15, 20, null]);
  return {
    venue_id: v.license_id,
    name: v.name.replace(/\s+/g, ' ').trim(),
    display_name: o.display_name ?? cleanName(v.name),
    address: `${v.address.replace(/\s+/g, ' ').trim()}, New York, NY ${v.zip}`,
    style, genres, price_level: price, typical_cover_usd: cover,
    has_dance_floor: dance,
    capacity: la ? Number(la.capacity) : 60 + Math.floor(rnd() * 240),
    lat: Number(v.lat), lon: Number(v.lon),
    opening_hours: null,
    is_claimed: o.is_claimed ?? 0,
    // Real public signal (311 noise complaints), normalised; shown only on the profile.
    complaint_risk: round((Number(v.noise_complaints) || 0) / maxNoise, 2),
    is_synthetic: 1,
  };
});

// ---------- states: every 30 min Sat Nov 14 20:00 -> Sun 03:00 ----------
const start = Date.parse('2026-11-14T20:00:00-05:00');
const SNAPS = Array.from({ length: 15 }, (_, i) => new Date(start + i * 30 * 60e3));
const DEMO_IDX = 7; // 23:30
const STORY = {
  '0370-21-116653': { peak: 6.5, amp: 0.95, conf: 0.71, fresh: 12, nRep: 4, line: 10, cover: null, genre: ['hip-hop', 'r&b'], vibe2230: 78 },
  '0370-24-136564': { peak: 8, amp: 1, conf: 0.8, fresh: 8, nRep: 6, line: 30, cover: 40, genre: ['house'] },
  '0370-23-131873': { peak: 7, amp: 0.4, conf: 0.26, fresh: 47, nRep: 1, line: 0, cover: 0, genre: null },
  '0370-23-127248': { peak: 8, amp: 0.85, conf: 0.62, fresh: 18, nRep: 3, line: 5, cover: 10, genre: ['throwbacks'] },
};
const states = [];
for (const v of venues) {
  const s = STORY[v.venue_id];
  const peak = s?.peak ?? 3 + rnd() * 9; // snapshot index of peak energy
  const amp = s?.amp ?? 0.3 + rnd() * 0.7;
  const baseConf = s?.conf ?? (rnd() < 0.25 ? 0.08 + rnd() * 0.3 : 0.4 + rnd() * 0.45);
  SNAPS.forEach((t, i) => {
    const curve = Math.exp(-((i - peak) ** 2) / 12) * amp;
    let vibe = round(clamp(12 + curve * 82 + (rnd() - 0.5) * 8, 0, 100));
    if (s?.vibe2230 && i === 5) vibe = s.vibe2230;
    const crowd = round(clamp(1 + curve * 4 + (rnd() - 0.5) * 0.4, 1, 5), 1);
    const conf = round(clamp(baseConf + (rnd() - 0.5) * 0.08 + (i < 2 ? -0.15 : 0), 0.05, 0.95), 2);
    const freshness = s?.fresh != null && Math.abs(i - DEMO_IDX) <= 2 ? s.fresh : Math.round(5 + (1 - conf) * 80 + rnd() * 15);
    const nRep = s?.nRep ?? Math.max(0, Math.round(conf * 7 + (rnd() - 0.5) * 2));
    const noData = nRep === 0 || conf < 0.12;
    const nul = () => rnd() < 0.2;
    const display = noData || conf < 0.2 ? 'none' : conf < 0.4 ? 'low' : 'show';
    const prev = i > 0 ? Math.exp(-((i - 1 - peak) ** 2) / 12) : curve;
    const d = curve - prev;
    states.push({
      venue_id: v.venue_id,
      snapshot_ts: iso(t),
      crowd: noData ? null : crowd,
      dancing: noData || !v.has_dance_floor ? (noData ? null : 0) : round(clamp(curve * 2, 0, 2), 1),
      line_minutes: noData ? null : s?.line ?? (nul() ? null : Math.round(clamp(curve * 35 - 5, 0, 40) / 5) * 5),
      cover_usd: noData ? null : s && 'cover' in s ? s.cover : nul() ? null : v.typical_cover_usd,
      music_genres: noData ? [] : s?.genre ?? (nul() ? [] : v.genres.slice(0, 1)),
      vibe_score: noData ? null : vibe,
      confidence: noData ? round(conf * 0.5, 2) : conf,
      freshness_minutes: noData ? null : freshness,
      n_reports: nRep,
      trend: noData ? null : d > 0.04 ? 'rising' : d < -0.04 ? 'falling' : 'steady',
      sources: noData ? [] : v.is_claimed ? ['scout', 'venue_update'] : ['scout'],
      display,
      is_synthetic: 1,
    });
  });
}

// ---------- scouts / reports ----------
const FIRST = ['Maya', 'Jules', 'Dev', 'Rosa', 'Kenji', 'Ari', 'Sam', 'Noor', 'Theo', 'Lena', 'Omar', 'Zoe', 'Ravi', 'Ivy', 'Marco', 'Tess', 'Kofi', 'Bea', 'Leo', 'Nia', 'Ezra', 'Ana', 'Finn', 'Sky', 'Jade'];
const scouts = FIRST.map((n, i) => {
  const pts = Math.round(2400 * Math.exp(-i / 7) + rnd() * 60);
  return {
    scout_id: `syn-s-${String(i + 1).padStart(4, '0')}`,
    display_name: `${n} ${String.fromCharCode(65 + Math.floor(rnd() * 26))}.`,
    level: pts > 1500 ? 5 : pts > 900 ? 4 : pts > 450 ? 3 : pts > 200 ? 2 : 1,
    points: pts,
    points_week: Math.round(pts * (0.08 + rnd() * 0.15)),
    reputation: round(0.45 + rnd() * 0.5, 2),
    is_synthetic: 1,
  };
});
// SYNTHETIC: the demo scout persona (demo-login display_name "Demo Scout").
scouts.push({ scout_id: 'syn-s-demo', display_name: 'Demo Scout', level: 1, points: 60, points_week: 20, reputation: 0.5, is_synthetic: 1 });

const reports = [];
let rid = 1;
for (const v of venues) {
  for (let i = 0; i < SNAPS.length; i++) {
    const st = states.find((s) => s.venue_id === v.venue_id && s.snapshot_ts === iso(SNAPS[i]));
    if (!st || st.crowd === null || rnd() > 0.55) continue;
    const t = new Date(SNAPS[i].getTime() - Math.floor(rnd() * 25) * 60e3);
    const sc = pick(scouts.slice(0, 25));
    reports.push({
      report_id: `syn-r-${String(rid++).padStart(6, '0')}`,
      venue_id: v.venue_id,
      scout_id: sc.scout_id,
      scout_level: sc.level,
      ts: iso(t),
      crowd: clamp(Math.round(st.crowd + (rnd() - 0.5)), 1, 5),
      dancing: st.dancing === null ? 0 : clamp(Math.round(st.dancing), 0, 2),
      line_minutes: st.line_minutes ?? 0,
      cover_usd: rnd() < 0.5 ? st.cover_usd : null,
      music_genre: st.music_genres[0] ?? null,
      verified_presence: rnd() < 0.8 ? 1 : 0,
      status: 'accepted',
      is_synthetic: 1,
    });
  }
}

// ---------- recommendations for 3 preset prefs (hand-tuned fixture ranking, NOT app logic) ----------
const PRESETS = {
  'hip-hop-dancers': { genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, max_cover_usd: 20, max_line_minutes: 15, max_distance_km: 1.5 },
  'cocktail-chill': { genres: ['jazz', 'soul-funk'], want_dancing: false, crowd_pref: 2, max_cover_usd: 10, max_line_minutes: 10, max_distance_km: 1 },
  'cheap-close': { genres: [], want_dancing: false, crowd_pref: 3, max_cover_usd: 0, max_line_minutes: 10, max_distance_km: 0.5 },
};
const LES = { lat: 40.7203, lon: -73.9881 };
const recommendations = {};
for (const [key, p] of Object.entries(PRESETS)) {
  recommendations[key] = SNAPS.map((t) => {
    const ts = iso(t);
    const rows = venues.map((v) => {
      const st = states.find((s) => s.venue_id === v.venue_id && s.snapshot_ts === ts);
      const dist = round(haversineKm(LES, v), 2);
      const reasons = [], missing = [];
      let m = 0.0, w = 0;
      const add = (score, weight) => { m += score * weight; w += weight; };
      const g = p.genres.length ? v.genres.filter((x) => p.genres.includes(x)) : [];
      if (p.genres.length) {
        const live = st.music_genres.filter((x) => p.genres.includes(x));
        if (live.length) { add(1, 3); reasons.push(`${label(live[0])} playing (${st.n_reports} reports, ${st.freshness_minutes} min ago)`); }
        else if (g.length) { add(0.7, 3); reasons.push(`Usually plays ${g.join(' & ')}`); }
        else if (!st.music_genres.length) { add(0.4, 3); missing.push('music not reported tonight'); }
        else add(0.1, 3);
      }
      if (st.crowd === null) { add(0.4, 2); missing.push('crowd not reported tonight'); }
      else { const c = 1 - Math.abs(st.crowd - p.crowd_pref) / 4; add(c, 2); if (c > 0.8) reasons.push(`Crowd ${st.crowd.toFixed(1)}/5, close to your ${p.crowd_pref}`); }
      if (p.want_dancing) {
        if (st.dancing === null) { add(0.4, 2); missing.push('dancing not reported'); }
        else { add(st.dancing / 2, 2); if (st.dancing >= 1) reasons.push(st.dancing >= 1.5 ? 'Lots of dancing' : 'Some dancing'); }
      }
      if (st.line_minutes === null) { add(0.4, 1); missing.push('line not reported'); }
      else { add(st.line_minutes <= p.max_line_minutes ? 1 : 0, 1); if (st.line_minutes <= p.max_line_minutes) reasons.push(st.line_minutes === 0 ? 'No line' : `Line ~${st.line_minutes} min, under your ${p.max_line_minutes}`); }
      if (st.cover_usd === null) { add(0.4, 1); missing.push('cover not reported tonight'); }
      else { add(st.cover_usd <= p.max_cover_usd ? 1 : 0, 1); if (st.cover_usd <= p.max_cover_usd) reasons.push(st.cover_usd === 0 ? 'No cover' : `Cover $${st.cover_usd}, within budget`); }
      add(clamp(1 - dist / (p.max_distance_km * 1.6), 0, 1), 1);
      let match = Math.round((m / w) * 100);
      if (v.venue_id === '0370-21-116653' && key === 'hip-hop-dancers') match = 91; // demo story
      let excluded_reason = null;
      if (st.line_minutes !== null && st.line_minutes > p.max_line_minutes) excluded_reason = `Line ~${st.line_minutes} min, over your ${p.max_line_minutes}-min limit`;
      else if (st.cover_usd !== null && st.cover_usd > p.max_cover_usd) excluded_reason = `Cover $${st.cover_usd}, over your $${p.max_cover_usd} limit`;
      else if (dist > p.max_distance_km) excluded_reason = `${dist} km away, beyond your ${p.max_distance_km} km`;
      const conf = st.confidence ?? 0;
      return {
        venue_id: v.venue_id, name: v.display_name,
        match_score: match, vibe_score: st.vibe_score, confidence: st.confidence,
        distance_km: dist, reasons: reasons.slice(0, 4), missing,
        excluded: excluded_reason !== null, excluded_reason,
        rank_score: round(match * (0.75 + 0.25 * conf), 1), // CONTRACTS §A rank formula
        freshness_minutes: st.freshness_minutes, display: st.display, n_reports: st.n_reports,
        cluster_label: v.style === 'club' ? 'Dance clubs' : v.style === 'cocktail' ? 'Cocktail bars' : 'Neighbourhood bars',
        complaint_risk: v.complaint_risk,
        is_synthetic: 1,
      };
    });
    const inc = rows.filter((r) => !r.excluded).sort((a, b) => b.rank_score - a.rank_score);
    const exc = rows.filter((r) => r.excluded).sort((a, b) => b.rank_score - a.rank_score).slice(0, 3);
    return { snapshot_ts: ts, results: [...inc, ...exc].map((r, i) => ({ ...r, rank: i + 1 })) };
  });
}

// ---------- bounties on lowest-confidence venues at 23:30 ----------
const demoStates = states.filter((s) => s.snapshot_ts === iso(SNAPS[DEMO_IDX])).sort((a, b) => (a.confidence ?? 0) - (b.confidence ?? 0));
const bountyVenues = ['0370-23-131873', ...demoStates.map((s) => s.venue_id).filter((id) => id !== '0370-23-131873')].slice(0, 6);
const bounties = bountyVenues.map((id, i) => ({
  bounty_id: `syn-b-${String(i + 1).padStart(4, '0')}`,
  venue_id: id,
  venue_name: venues.find((v) => v.venue_id === id).display_name,
  created_at: iso(new Date(SNAPS[DEMO_IDX].getTime() - (20 + i * 15) * 60e3)),
  expires_at: iso(new Date(SNAPS[DEMO_IDX].getTime() + (40 + i * 25) * 60e3)),
  points: i === 0 ? 50 : pick([20, 25, 30, 40]),
  reason: i === 0 ? 'Low confidence: only 1 report in the last hour' : pick(['No fresh reports in 60+ min', 'Low confidence tonight', 'Cover not reported tonight']),
  claimed_by: null, claimed_at: null,
  is_synthetic: 1,
}));

// ---------- owner dashboards ----------
const HOURS = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3];
const owner = Object.fromEntries(venues.map((v) => {
  const scale = 0.5 + rnd();
  return [v.venue_id, {
    venue_id: v.venue_id,
    views: Math.round(420 * scale), taps: Math.round(96 * scale), saves: Math.round(31 * scale),
    reports_tonight: reports.filter((r) => r.venue_id === v.venue_id).length,
    rec_appearances: Math.round(260 * scale),
    demand_by_hour: HOURS.map((h, i) => ({ hour: h, value: Math.round(scale * 100 * Math.exp(-((i - 5.5) ** 2) / 5) + rnd() * 6) })),
    is_synthetic: 1,
  }];
}));

const meta = { generated_by: 'frontend/scripts/build-fixtures.mjs', seed: 42, source: usingLiveSim ? 'live-sim CSVs + launch_venues.csv' : 'seeded generator + launch_venues.csv', is_synthetic: 1 };
const write = (n, d) => writeFileSync(join(out, n), JSON.stringify(d) + '\n');
write('syn_venues.json', { meta, rows: venues });
write('syn_states.json', { meta, rows: states });
write('syn_reports.json', { meta, rows: reports });
write('syn_leaderboard.json', { meta, rows: scouts });
write('syn_bounties.json', { meta, rows: bounties });
write('syn_owner_dashboard.json', { meta, rows: owner });
write('syn_recommendations.json', { meta, presets: PRESETS, rows: recommendations });
console.log(`fixtures: ${venues.length} venues, ${states.length} states, ${reports.length} reports, ${bounties.length} bounties (${meta.source})`);
