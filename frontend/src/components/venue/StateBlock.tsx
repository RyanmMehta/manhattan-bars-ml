import { dancingLabel } from '../../api/adapters';
import type { LiveVenueState } from '../../api/types';
import { genreLabel } from '../../config/genres';
import { Stat } from '../ui/Stat';
import { Unknown } from '../ui/Unknown';
import { TrendArrow } from './TrendArrow';

export function StateBlock({ s }: { s: LiveVenueState | null }) {
  if (!s) return <p className="text-sm text-muted">No live state for this venue tonight.</p>;
  const dl = dancingLabel(s.dancing);
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <Stat label="Crowd">{s.crowd !== null ? `${s.crowd.toFixed(1)} / 5` : <Unknown />}</Stat>
      <Stat label="Dancing">{dl ?? <Unknown />}</Stat>
      <Stat label="Line">{s.line_minutes !== null ? `~${s.line_minutes} min` : <Unknown />}</Stat>
      <Stat label="Cover">{s.cover_usd !== null ? (s.cover_usd === 0 ? 'Free' : `$${s.cover_usd}`) : <Unknown />}</Stat>
      <Stat label="Music">{s.music_genres && s.music_genres.length ? s.music_genres.map(genreLabel).join(', ') : <Unknown />}</Stat>
      <Stat label="Trend"><TrendArrow trend={s.trend} /></Stat>
      <Stat label="Reports">{s.n_reports}</Stat>
      <Stat label="Sources">{s.sources.length ? s.sources.join(', ').replace('venue_update', 'venue') : <Unknown />}</Stat>
    </dl>
  );
}
