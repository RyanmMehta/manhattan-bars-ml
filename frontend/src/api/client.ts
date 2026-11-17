// The single typed API client (PRD F1). No fetch calls anywhere else.
import { env } from '../config/env';
import { TOKEN_TTL_MS } from '../config/thresholds';
import type * as T from './types';
import * as guard from './adapters';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: unknown = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface ListResult<R> {
  rows: R[];
  total: number | null;
  data: T.DataHeader;
}

type Query = Record<string, string | number | boolean | null | undefined>;

let base = env.apiBase;
let nowProvider: () => string | null = () => null;
const dataListeners = new Set<(d: T.DataHeader) => void>();

export function configureClient(opts: { base?: string; now?: () => string | null }) {
  if (opts.base !== undefined) base = opts.base;
  if (opts.now) nowProvider = opts.now;
}
export function onDataHeader(fn: (d: T.DataHeader) => void): () => void {
  dataListeners.add(fn);
  return () => dataListeners.delete(fn);
}

// ---------- token (RULES §3: localStorage na.token.v1, 24 h) ----------
const TOKEN_KEY = 'na.token.v1';
export interface StoredToken {
  token: string;
  issued_at: number;
  role: T.Role;
  id: string | null;
  venue_id?: string | null;
  display_name: string;
}
export function getToken(nowMs = Date.now()): StoredToken | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const t = JSON.parse(raw) as StoredToken;
    if (typeof t.token !== 'string' || nowMs - t.issued_at > TOKEN_TTL_MS) return null;
    return t;
  } catch {
    return null;
  }
}
export function setToken(t: StoredToken | null) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, JSON.stringify(t));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export function buildUrl(path: string, query: Query = {}, withNow = true): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue;
    q.set(k, String(v));
  }
  const now = withNow ? nowProvider() : null;
  if (now && !q.has('now')) q.set('now', now);
  const qs = q.toString();
  return `${base.replace(/\/$/, '')}${path}${qs ? `?${qs}` : ''}`;
}

async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* not json */
  }
  const e = guard.asErrorEnvelope(body);
  if (e) return new ApiError(res.status, e.code, e.message, e.details);
  return new ApiError(res.status, res.status === 401 ? 'unauthorized' : 'http_error', `Request failed (${res.status})`);
}

async function request(
  method: 'GET' | 'POST',
  path: string,
  opts: { query?: Query; body?: unknown; auth?: boolean; signal?: AbortSignal } = {},
): Promise<{ json: unknown; res: Response }> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  if (opts.auth) {
    const t = getToken();
    if (!t) throw new ApiError(401, 'login_required', 'Log in as a demo persona first');
    headers.Authorization = `Bearer ${t.token}`;
  }
  // Every GET appends `now` (CONTRACTS §B); POSTs carry it too so the mock/backend replay matches.
  const url = buildUrl(path, opts.query, true);
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, 'network', 'Network error: the API is unreachable');
  }
  if (!res.ok) throw await parseError(res);
  const d = res.headers.get('X-Data');
  if (d === 'synthetic' || d === 'real' || d === 'mixed') dataListeners.forEach((fn) => fn(d));
  const json: unknown = res.status === 204 ? null : await res.json();
  return { json, res };
}

function check<R>(v: unknown, g: (x: unknown) => x is R, what: string): R {
  if (!g(v)) throw new ApiError(500, 'bad_shape', `Unexpected ${what} response shape`);
  return v;
}
function checkList<R>(v: unknown, g: (x: unknown) => x is R, what: string): R[] {
  if (!Array.isArray(v)) throw new ApiError(500, 'bad_shape', `Expected a list of ${what}`);
  return v.map((x) => check(x, g, what));
}

export const api = {
  async health(signal?: AbortSignal): Promise<T.Health> {
    const { json } = await request('GET', '/health', { signal });
    return check(json, guard.isHealth, 'health');
  },
  async demoLogin(input: T.DemoLoginInput): Promise<T.DemoLoginResult> {
    const { json } = await request('POST', '/auth/demo-login', { body: input });
    return check(json, guard.isDemoLogin, 'demo-login');
  },
  async venues(
    p: { q?: string; style?: string; genre?: string; lat?: number; lon?: number; limit?: number; offset?: number } = {},
  ): Promise<ListResult<T.VenueCard>> {
    const { json, res } = await request('GET', '/venues', { query: { launch_only: true, ...p } });
    const total = res.headers.get('X-Total-Count');
    const d = res.headers.get('X-Data');
    return {
      rows: checkList(json, guard.isVenueCard, 'venue card'),
      total: total === null ? null : Number(total),
      data: d === 'synthetic' || d === 'real' || d === 'mixed' ? d : null,
    };
  },
  async venue(id: string): Promise<T.VenueDetail> {
    const { json } = await request('GET', `/venues/${encodeURIComponent(id)}`);
    return check(json, guard.isVenueDetail, 'venue detail');
  },
  async venueState(id: string): Promise<T.LiveVenueState> {
    const { json } = await request('GET', `/venues/${encodeURIComponent(id)}/state`);
    return check(json, guard.isLiveState, 'live state');
  },
  async recommend(prefs: T.Preferences): Promise<T.Recommendation[]> {
    const { json } = await request('POST', '/recommend', { body: prefs });
    return checkList(json, guard.isRecommendation, 'recommendation');
  },
  async planNight(prefs: T.Preferences & { n_stops: number }): Promise<T.PlanStop[]> {
    const { json } = await request('POST', '/plan-night', { body: prefs });
    return checkList(json, guard.isPlanStop, 'plan stop');
  },
  async report(input: T.ReportInput): Promise<T.ReportResult> {
    const { json } = await request('POST', '/reports', { body: input, auth: true });
    return check(json, guard.isReportResult, 'report');
  },
  async feedback(input: T.FeedbackInput): Promise<unknown> {
    const { json } = await request('POST', '/feedback', { body: input, auth: true });
    return json;
  },
  async leaderboard(): Promise<T.LeaderboardRow[]> {
    const { json } = await request('GET', '/scouts/leaderboard');
    return checkList(json, guard.isLeaderboardRow, 'leaderboard row');
  },
  async bounties(): Promise<T.Bounty[]> {
    const { json } = await request('GET', '/bounties');
    return checkList(json, guard.isBounty, 'bounty');
  },
  async ownerDashboard(id: string): Promise<T.OwnerDashboard> {
    const { json } = await request('GET', `/owner/${encodeURIComponent(id)}/dashboard`);
    return check(json, guard.isOwnerDashboard, 'owner dashboard');
  },
  async ownerUpdate(id: string, u: Omit<T.VenueUpdate, 'update_id' | 'ts' | 'venue_id'>): Promise<unknown> {
    const { json } = await request('POST', `/owner/${encodeURIComponent(id)}/updates`, { body: u, auth: true });
    return json;
  },
  async heatmap(byHour = false): Promise<T.HeatPoint[]> {
    const { json } = await request('GET', '/heatmap', { query: { by: byHour ? 'hour' : undefined } });
    return checkList(json, guard.isHeatPoint, 'heatmap point');
  },
};
