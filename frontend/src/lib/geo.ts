export interface LatLon {
  lat: number;
  lon: number;
}
/** Great-circle distance in metres. */
export function haversineM(a: LatLon, b: LatLon): number {
  const R = 6371000;
  const toR = (d: number) => (d * Math.PI) / 180;
  const dLat = toR(b.lat - a.lat);
  const dLon = toR(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a.lat)) * Math.cos(toR(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
/** Nearest venue to a point (used only to pre-select the vibe-check venue; the server verifies presence). */
export function nearest<V extends LatLon>(p: LatLon, list: V[]): { venue: V; meters: number } | null {
  let best: { venue: V; meters: number } | null = null;
  for (const v of list) {
    const m = haversineM(p, v);
    if (!best || m < best.meters) best = { venue: v, meters: m };
  }
  return best;
}
