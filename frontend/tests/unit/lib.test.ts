import { haversineM, nearest } from '../../src/lib/geo';
import { agoLabel, countdown, minutesAgo, shiftIso } from '../../src/lib/time';
import { decodePrefs, encodePrefs, shareUrl } from '../../src/lib/share';
import { directionsUrl } from '../../src/lib/mapsLink';
import { DEFAULT_PREFS } from '../../src/state/prefsReducer';

describe('geo', () => {
  it('haversine ~111 m per 0.001 lat', () => expect(haversineM({ lat: 40.7, lon: -74 }, { lat: 40.701, lon: -74 })).toBeCloseTo(111, 0));
  it('nearest', () => {
    const r = nearest({ lat: 40.7, lon: -74 }, [{ id: 'a', lat: 40.71, lon: -74 }, { id: 'b', lat: 40.7001, lon: -74 }]);
    expect(r?.venue.id).toBe('b');
    expect(nearest({ lat: 0, lon: 0 }, [])).toBeNull();
  });
});
describe('time', () => {
  const now = '2026-11-14T23:30:00-05:00';
  it('minutes ago + labels', () => {
    expect(minutesAgo('2026-11-14T23:18:00-05:00', now)).toBe(12);
    expect(agoLabel(12)).toBe('12 min ago');
    expect(agoLabel(0)).toBe('just now');
    expect(agoLabel(75)).toBe('1 h 15 min ago');
    expect(agoLabel(null)).toBeNull();
  });
  it('shift + countdown', () => {
    expect(shiftIso(now, -60)).toBe('2026-11-14T22:30:00-05:00');
    expect(countdown('2026-11-15T00:10:00-05:00', now)).toBe('40 min left');
    expect(countdown('2026-11-14T23:00:00-05:00', now)).toBe('expired');
    expect(countdown(null, now)).toBeNull();
  });
});
describe('share links (US-02 AC7)', () => {
  it('round-trips prefs as base64url', () => {
    const p = { ...DEFAULT_PREFS, genres: ['r&b', 'hip-hop'] };
    const enc = encodePrefs(p);
    expect(enc).not.toMatch(/[+/=]/);
    expect(decodePrefs(enc)).toEqual(p);
    expect(decodePrefs('garbage!!')).toBeNull();
    expect(decodePrefs(null)).toBeNull();
  });
  it('carries now and prefs', () => {
    const u = new URL(shareUrl('/tonight', '2026-11-14T23:30:00-05:00', DEFAULT_PREFS, 'https://x.test'));
    expect(u.pathname).toBe('/tonight');
    expect(u.searchParams.get('now')).toBe('2026-11-14T23:30:00-05:00');
    expect(decodePrefs(u.searchParams.get('prefs'))).toEqual(DEFAULT_PREFS);
  });
  it('directions link', () => {
    expect(directionsUrl({ lat: 1, lon: 2, name: 'X' }, 'Android')).toContain('google.com/maps/dir');
    expect(directionsUrl({ lat: 1, lon: 2, name: 'X' }, 'iPhone')).toContain('maps.apple.com');
  });
});
