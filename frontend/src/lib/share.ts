import type { Preferences } from '../api/types';

export function encodePrefs(p: Preferences): string {
  const json = JSON.stringify(p);
  const b64 = btoa(unescape(encodeURIComponent(json)));
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function decodePrefs(s: string | null): Preferences | null {
  if (!s) return null;
  try {
    const b64 = s.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(escape(atob(b64)));
    const v: unknown = JSON.parse(json);
    if (typeof v === 'object' && v !== null && Array.isArray((v as Preferences).genres)) return v as Preferences;
    return null;
  } catch {
    return null;
  }
}
/** PRD US-02 AC7 share links carry now + prefs. */
export function shareUrl(path: string, now: string | null, prefs: Preferences, origin = window.location.origin): string {
  const q = new URLSearchParams();
  if (now) q.set('now', now);
  q.set('prefs', encodePrefs(prefs));
  return `${origin}${path}?${q.toString()}`;
}
