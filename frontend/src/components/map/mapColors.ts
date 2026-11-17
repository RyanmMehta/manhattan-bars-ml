import { CONF_SHOW } from '../../config/thresholds';

/** Read design tokens from CSS so no hex literals live in TS (RULES §3). */
export function token(name: string): string {
  if (typeof window === 'undefined') return 'gray';
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || 'gray';
}

export function vibeColorVar(vibe: number | null): string {
  if (vibe === null) return 'var(--c-none)';
  if (vibe < 35) return 'var(--c-chill)';
  if (vibe < 65) return 'var(--c-lively)';
  return 'var(--c-packed)';
}

/** Dot radius grows with confidence; low-confidence dots are drawn hollow. */
export function dotRadius(conf: number | null): number {
  return 5 + Math.round((conf === null ? 0 : conf) * 9);
}
export function isHollow(conf: number | null): boolean {
  return conf === null || conf < CONF_SHOW;
}
