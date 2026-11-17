// Reserved env names only (CONTRACTS §H).
export type ApiMode = 'mock' | 'live';

function urlFlag(name: string): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get(name);
}

export function apiMode(): ApiMode {
  const q = urlFlag('mock');
  if (q === '1') return 'mock';
  if (q === '0') return 'live';
  try {
    const s = sessionStorage.getItem('na.mode.v1');
    if (s === 'mock' || s === 'live') return s;
  } catch {
    /* storage blocked */
  }
  return import.meta.env.VITE_API_MODE === 'live' ? 'live' : 'mock';
}

export const env = {
  apiBase: (import.meta.env.VITE_API_BASE as string | undefined) || '/api',
  demoNow: (import.meta.env.VITE_DEMO_NOW as string | undefined) || null,
  featureRouting: import.meta.env.VITE_FEATURE_ROUTING === '1',
  featureHeatmap: import.meta.env.VITE_FEATURE_HEATMAP !== '0',
};
