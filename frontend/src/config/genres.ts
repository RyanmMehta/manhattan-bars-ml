// Shared genre vocabulary (CONTRACTS §E, owned by live-sim at simulator/config/genres.json).
// Copied from CONTRACTS until simulator/config/genres.json exists on the integration branch.
export const GENRES = [
  'hip-hop', 'r&b', 'afrobeats', 'latin', 'reggaeton', 'house', 'techno', 'edm', 'disco',
  'pop', 'top-40', 'throwbacks', 'indie', 'rock', 'punk', 'jazz', 'soul-funk',
] as const;
export type Genre = (typeof GENRES)[number];

const LABELS: Record<string, string> = {
  'hip-hop': 'Hip-hop', 'r&b': 'R&B', edm: 'EDM', 'top-40': 'Top 40', 'soul-funk': 'Soul/funk',
};
export function genreLabel(g: string): string {
  return LABELS[g] ?? g.charAt(0).toUpperCase() + g.slice(1);
}
export const STYLES = ['dive', 'cocktail', 'club', 'lounge', 'pub', 'restaurant-bar'] as const;
export function styleLabel(s: string | null | undefined): string {
  if (!s) return 'Bar';
  return s === 'restaurant-bar' ? 'Restaurant bar' : s.charAt(0).toUpperCase() + s.slice(1);
}
