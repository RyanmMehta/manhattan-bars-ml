/** Parse an ISO timestamp; returns ms or NaN. */
export const ms = (iso: string) => Date.parse(iso);

export function minutesAgo(iso: string, nowIso: string): number {
  return Math.max(0, Math.round((ms(nowIso) - ms(iso)) / 60000));
}
export function agoLabel(min: number | null | undefined): string | null {
  if (min === null || min === undefined) return null;
  if (min < 1) return 'just now';
  if (min < 60) return `${min} min ago`;
  const h = Math.floor(min / 60);
  return `${h} h ${min % 60 ? `${min % 60} min ` : ''}ago`;
}
/** Wall-clock time in New York, e.g. "11:30 PM". */
export function clockLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
}
export function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'America/New_York' });
}
/** Shift an ISO timestamp by minutes, returned in -05:00 (EST in Nov 2026). */
export function shiftIso(iso: string, minutes: number): string {
  const t = new Date(ms(iso) + minutes * 60000 - 5 * 3600000);
  return `${t.toISOString().slice(0, 19)}-05:00`;
}
export function countdown(untilIso: string | null, nowIso: string): string | null {
  if (!untilIso) return null;
  const m = Math.round((ms(untilIso) - ms(nowIso)) / 60000);
  if (m <= 0) return 'expired';
  return m < 60 ? `${m} min left` : `${Math.floor(m / 60)} h ${m % 60} min left`;
}
