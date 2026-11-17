import { useEffect, useMemo, useState } from 'react';
import { venueName } from '../api/adapters';
import { useVenues } from '../api/queries';
import type { VenueCard as Card } from '../api/types';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { FilterBar, type FilterValue } from '../components/venue/FilterBar';
import { VenueCard } from '../components/venue/VenueCard';
import { SEARCH_DEBOUNCE_MS } from '../config/thresholds';
import { usePrefs } from '../state/prefs';

const EMPTY: FilterValue = { q: '', style: '', genre: '', sort: 'vibe' };

/** Client-side sort on returned fields only (RULES §3). Unknown vibe sorts last. */
function sortRows(rows: Card[], key: FilterValue['sort']): Card[] {
  if (key === 'distance') return rows; // server order when lat/lon are sent (CONTRACTS §J)
  const copy = [...rows];
  if (key === 'name') return copy.sort((a, b) => venueName(a).localeCompare(venueName(b)));
  const vibe = (c: Card) => (c.state && c.state.vibe_score !== null ? c.state.vibe_score : -1);
  return copy.sort((a, b) => vibe(b) - vibe(a));
}

/** US-03: browse, filter, search. */
export function Browse() {
  const { prefs } = usePrefs();
  const [f, setF] = useState<FilterValue>(EMPTY);
  const [q, setQ] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setQ(f.q.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [f.q]);
  const res = useVenues({
    q: q || undefined,
    style: f.style || undefined,
    genre: f.genre || undefined,
    lat: prefs.lat,
    lon: prefs.lon,
  });
  const rows = useMemo(() => (res.data ? sortRows(res.data.rows, f.sort) : []), [res.data, f.sort]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold">Browse the LES</h1>
        {res.data && (
          <span className="text-xs text-muted" data-testid="venue-count">
            {res.data.total ?? rows.length} venues
          </span>
        )}
      </div>
      <FilterBar value={f} onChange={setF} />
      {res.data?.data && res.data.data !== 'real' && (
        <div className="flex justify-end">
          <DemoBadge force />
        </div>
      )}
      {res.isPending ? (
        <Skeleton lines={4} className="h-28" />
      ) : res.isError ? (
        <ErrorState error={res.error} onRetry={() => void res.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No venues match"
          body="Try a different search or fewer filters."
          action={
            <Button variant="secondary" onClick={() => setF(EMPTY)}>
              Clear filters
            </Button>
          }
        />
      ) : (
        <ul className="space-y-2">
          {rows.map((v) => (
            <VenueCard key={v.venue_id} venue={v} />
          ))}
        </ul>
      )}
    </div>
  );
}
