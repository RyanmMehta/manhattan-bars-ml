export function directionsUrl(v: { lat: number; lon: number; name: string }, ua = typeof navigator !== 'undefined' ? navigator.userAgent : ''): string {
  if (/iPhone|iPad|Macintosh/.test(ua)) {
    return `https://maps.apple.com/?daddr=${v.lat},${v.lon}&q=${encodeURIComponent(v.name)}&dirflg=w`;
  }
  return `https://www.google.com/maps/dir/?api=1&destination=${v.lat},${v.lon}&travelmode=walking`;
}
