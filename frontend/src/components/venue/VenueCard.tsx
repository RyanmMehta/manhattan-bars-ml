import { Link } from 'react-router-dom';
import { displayBand, venueName } from '../../api/adapters';
import type { VenueCard as Card } from '../../api/types';
import { genreLabel, styleLabel } from '../../config/genres';
import { DemoBadge } from '../demo/DemoBadge';
import { Unknown } from '../ui/Unknown';
import { ConfidenceMeter } from './ConfidenceMeter';
import { FreshnessTag } from './FreshnessTag';
import { VibeBadge } from './VibeBadge';

export function VenueCard({ venue }: { venue: Card }) {
  const s = venue.state;
  const band = displayBand(s);
  return (
    <li data-testid="venue-card" className="rounded-lg border border-line bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Link to={`/venue/${venue.venue_id}`} className="block font-display text-base font-semibold hover:text-accent">{venueName(venue)}</Link>
          <p className="truncate text-xs text-muted">
            {styleLabel(venue.style)}{venue.genres.length ? ` · ${venue.genres.map(genreLabel).join(', ')}` : ''}
            {venue.distance_km !== undefined && venue.distance_km !== null ? ` · ${venue.distance_km.toFixed(1)} km` : ''}
          </p>
        </div>
        <VibeBadge vibe={s ? s.vibe_score : null} confidence={s ? s.confidence : null} display={s?.display} />
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div><dt className="text-muted">Line</dt><dd>{s && s.line_minutes !== null ? `~${s.line_minutes} min` : <Unknown />}</dd></div>
        <div><dt className="text-muted">Cover</dt><dd>{s && s.cover_usd !== null ? (s.cover_usd === 0 ? 'Free' : `$${s.cover_usd}`) : <Unknown />}</dd></div>
        <div><dt className="text-muted">Confidence</dt><dd><ConfidenceMeter confidence={s ? s.confidence : null} /></dd></div>
      </dl>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <FreshnessTag minutes={s ? s.freshness_minutes : null} nReports={band === 'none' ? undefined : s?.n_reports} />
        <DemoBadge data={venue} />
      </div>
    </li>
  );
}
