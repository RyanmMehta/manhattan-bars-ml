import type { Preferences } from '../api/types';
import { LES_CENTER } from '../config/thresholds';

export const PREFS_KEY = 'na.prefs.v1';

export const DEFAULT_PREFS: Preferences = {
  genres: [],
  want_dancing: false,
  crowd_pref: 3,
  max_cover_usd: 20,
  max_line_minutes: 15,
  max_distance_km: 1.5,
  lat: LES_CENTER.lat,
  lon: LES_CENTER.lon,
  group_size: 4,
};

export type PrefsAction =
  | { type: 'toggleGenre'; genre: string }
  | { type: 'set'; patch: Partial<Preferences> }
  | { type: 'reset' }
  | { type: 'replace'; prefs: Preferences };

export function prefsReducer(s: Preferences, a: PrefsAction): Preferences {
  switch (a.type) {
    case 'toggleGenre':
      return { ...s, genres: s.genres.includes(a.genre) ? s.genres.filter((g) => g !== a.genre) : [...s.genres, a.genre] };
    case 'set': {
      const n = { ...s, ...a.patch };
      n.crowd_pref = Math.min(5, Math.max(1, Math.round(n.crowd_pref)));
      n.group_size = Math.min(12, Math.max(1, Math.round(n.group_size)));
      return n;
    }
    case 'reset':
      return DEFAULT_PREFS;
    case 'replace':
      return a.prefs;
  }
}

export function loadPrefs(): { prefs: Preferences; saved: boolean } {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return { prefs: DEFAULT_PREFS, saved: false };
    const v = JSON.parse(raw) as Partial<Preferences>;
    if (!Array.isArray(v.genres)) return { prefs: DEFAULT_PREFS, saved: false };
    return { prefs: { ...DEFAULT_PREFS, ...v }, saved: true };
  } catch {
    return { prefs: DEFAULT_PREFS, saved: false };
  }
}
export function savePrefs(p: Preferences) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(p));
  } catch {
    /* ignore */
  }
}
