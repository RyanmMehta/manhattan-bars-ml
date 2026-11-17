import type { VenueUpdate } from '../../api/types';
import { clockLabel } from '../../lib/time';
import { DemoBadge } from '../demo/DemoBadge';

export function OfferCard({ u }: { u: VenueUpdate }) {
  const genres = Array.isArray(u.genres) ? u.genres.join(', ') : u.genres;
  return (
    <div className="rounded-md border border-cyan/40 bg-raised p-3 text-sm" data-testid="offer-card">
      <div className="flex justify-between gap-2">
        <p className="font-semibold text-cyan">{u.offer ?? u.event ?? 'Venue update'}</p>
        <DemoBadge data={u} />
      </div>
      <p className="text-muted">
        {[u.cover_usd !== null ? `Cover $${u.cover_usd}` : null, u.dj ? `DJ ${u.dj}` : null, genres || null, u.event && u.offer ? u.event : null].filter(Boolean).join(' · ')}
      </p>
      {u.offer_expires_at && <p className="text-xs text-muted">Until {clockLabel(u.offer_expires_at)}</p>}
    </div>
  );
}
