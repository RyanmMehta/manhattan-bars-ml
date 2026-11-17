import { DEFAULT_PREFS, PREFS_KEY, loadPrefs, prefsReducer, savePrefs } from '../../src/state/prefsReducer';
import { enqueue, flushQueue, readQueue } from '../../src/state/offlineQueue';

beforeEach(() => localStorage.clear());

describe('prefs reducer (US-01)', () => {
  it('toggles genres', () => {
    const a = prefsReducer(DEFAULT_PREFS, { type: 'toggleGenre', genre: 'hip-hop' });
    expect(a.genres).toEqual(['hip-hop']);
    expect(prefsReducer(a, { type: 'toggleGenre', genre: 'hip-hop' }).genres).toEqual([]);
  });
  it('clamps crowd and group size', () => {
    const a = prefsReducer(DEFAULT_PREFS, { type: 'set', patch: { crowd_pref: 9, group_size: 0 } });
    expect(a.crowd_pref).toBe(5);
    expect(a.group_size).toBe(1);
  });
  it('reset/replace', () => {
    expect(prefsReducer({ ...DEFAULT_PREFS, crowd_pref: 1 }, { type: 'reset' })).toEqual(DEFAULT_PREFS);
    const p = { ...DEFAULT_PREFS, group_size: 7 };
    expect(prefsReducer(DEFAULT_PREFS, { type: 'replace', prefs: p })).toBe(p);
  });
  it('persists to localStorage na.prefs.v1', () => {
    expect(loadPrefs().saved).toBe(false);
    savePrefs({ ...DEFAULT_PREFS, genres: ['jazz'] });
    expect(JSON.parse(localStorage.getItem(PREFS_KEY)!).genres).toEqual(['jazz']);
    expect(loadPrefs()).toEqual({ prefs: { ...DEFAULT_PREFS, genres: ['jazz'] }, saved: true });
    localStorage.setItem(PREFS_KEY, '{bad');
    expect(loadPrefs().saved).toBe(false);
  });
});

describe('offline queue (US-06 AC5)', () => {
  const body = { venue_id: 'v', crowd: 3, dancing: 1, line_minutes: 5 };
  it('queues and sends', async () => {
    enqueue(body);
    expect(readQueue()).toHaveLength(1);
    const send = vi.fn().mockResolvedValue({});
    expect(await flushQueue(send)).toEqual({ sent: 1, dropped: 0 });
    expect(readQueue()).toHaveLength(0);
  });
  it('retries once then drops', async () => {
    enqueue(body);
    const fail = vi.fn().mockRejectedValue(new Error('x'));
    await flushQueue(fail);
    expect(readQueue()[0]?.attempts).toBe(1);
    expect(await flushQueue(fail)).toEqual({ sent: 0, dropped: 1 });
    expect(readQueue()).toHaveLength(0);
  });
});
