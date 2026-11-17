import { confidenceBars, dancingLabel, displayBand, isStale, isSynthetic, venueName, vibeLabel } from '../../src/api/adapters';
import { cleanVenueName } from '../../src/lib/names';
import { CONF_LOW, CONF_SHOW, STALE_MIN } from '../../src/config/thresholds';

describe('display band (CONTRACTS §A, US-02 AC4)', () => {
  it('prefers backend display', () => expect(displayBand({ display: 'low', confidence: 0.9, vibe_score: 80 })).toBe('low'));
  it('computes show/low/none from thresholds', () => {
    expect(displayBand({ confidence: CONF_SHOW, vibe_score: 50 })).toBe('show');
    expect(displayBand({ confidence: CONF_LOW, vibe_score: 50 })).toBe('low');
    expect(displayBand({ confidence: 0.19, vibe_score: 50 })).toBe('none');
    expect(displayBand({ confidence: 0.9, vibe_score: null })).toBe('none');
    expect(displayBand({ confidence: null, vibe_score: 40 })).toBe('none');
    expect(displayBand(null)).toBe('none');
  });
});
describe('vibe label bands (§J)', () => {
  it.each([[0, 'Chill'], [34, 'Chill'], [35, 'Lively'], [64, 'Lively'], [65, 'Packed'], [100, 'Packed']] as const)('%i → %s', (v, l) =>
    expect(vibeLabel(v)).toBe(l));
  it('null → no label', () => expect(vibeLabel(null)).toBeNull());
});
describe('misc helpers', () => {
  it('stale only above STALE_MIN', () => {
    expect(isStale(STALE_MIN)).toBe(false);
    expect(isStale(STALE_MIN + 1)).toBe(true);
    expect(isStale(null)).toBe(false);
  });
  it('confidence bars', () => {
    expect(confidenceBars(null)).toEqual({ bars: 0, label: null });
    expect(confidenceBars(0.1).label).toBe('Low');
    expect(confidenceBars(0.3).label).toBe('Some');
    expect(confidenceBars(0.6).label).toBe('Good');
    expect(confidenceBars(0.8).label).toBe('High');
  });
  it('synthetic flag', () => {
    expect(isSynthetic({ is_synthetic: 1 })).toBe(true);
    expect(isSynthetic({ is_synthetic: false })).toBe(false);
    expect(isSynthetic(null)).toBe(false);
  });
  it('dancing label keeps null unknown', () => {
    expect(dancingLabel(null)).toBeNull();
    expect(dancingLabel(1.4)).toBe('Some');
  });
});
describe('names (PRD F6)', () => {
  it('uses display_name when present', () => expect(venueName({ display_name: 'Attaboy', name: 'ATTABOY COCKTAILS LLC' })).toBe('Attaboy'));
  it('cleans legal names', () => {
    expect(cleanVenueName('ATTABOY COCKTAILS LLC')).toBe('Attaboy Cocktails');
    expect(cleanVenueName('Apt 5 LLC')).toBe('Apt 5');
    expect(cleanVenueName("IGGY'S KELTIC LOUNGE")).toBe("Iggy's Keltic Lounge");
    expect(venueName({ display_name: null, name: 'MR. FONG\'S' })).toBe("Mr. Fong's");
  });
});
