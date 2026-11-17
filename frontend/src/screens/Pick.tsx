import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { venueName } from '../api/adapters';
import { useRecommend, useVenues } from '../api/queries';
import type { Recommendation, VenueCard } from '../api/types';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { PickHero } from '../components/venue/PickHero';
import { VenueCardCompact } from '../components/venue/VenueCardCompact';
import { shareUrl } from '../lib/share';
import { clockLabel } from '../lib/time';
import { useDemoClock } from '../state/demoClock';
import { usePrefs } from '../state/prefs';

/** US-02: tonight's pick. Order follows the backend's `rank`; never re-ranked here. */
export function Pick() {
  const { prefs, fromUrl } = usePrefs();
  const { now } = useDemoClock();
  const q = useRecommend(prefs);
  // Backend 0d02a83+ sends display_name / freshness_minutes / n_reports on each row. Older backends don't:
  // only then join the venue cards (display only; order still comes from the backend's `rank`).
  const needJoin = !!q.data && q.data.some((r) => r.display_name === undefined || r.freshness_minutes === undefined);
  const cards = useVenues({ lat: prefs.lat, lon: prefs.lon }, needJoin);
  const byId = useMemo(() => new Map((cards.data?.rows ?? []).map((c) => [c.venue_id, c])), [cards.data]);
  const enrich = (r: Recommendation): Recommendation => {
    const c: VenueCard | undefined = byId.get(r.venue_id);
    const s = c?.state;
    return {
      ...r,
      name: r.display_name ? r.display_name : c ? venueName(c) : venueName({ name: r.name, display_name: null }),
      freshness_minutes: r.freshness_minutes !== undefined ? r.freshness_minutes : s ? s.freshness_minutes : undefined,
      n_reports: r.n_reports !== undefined ? r.n_reports : s ? s.n_reports : undefined,
      display: r.display ?? s?.display,
    };
  };
  const [showExcluded, setShowExcluded] = useState(false);
  const toast = useToast();

  const share = async () => {
    const url = shareUrl('/tonight', now, prefs);
    try {
      await navigator.clipboard.writeText(url);
      toast('Link copied: your group sees the same pick');
    } catch {
      toast(url, 'warn');
    }
  };

  if (q.isPending) return <Skeleton lines={3} className="h-40" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  const rows = [...q.data].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0)).map(enrich);
  const included = rows.filter((r) => !r.excluded);
  const excluded = rows.filter((r) => r.excluded);
  const [hero, ...rest] = included;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold">Where to now?</h1>
          <p className="text-xs text-muted">
            {now ? `As of ${clockLabel(now)}` : 'Live'}
            {fromUrl ? ' · shared prefs (read-only)' : ''}
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => void q.refetch()}
          aria-label="Refresh picks"
          disabled={q.isFetching}
        >
          {q.isFetching ? 'Refreshing…' : 'Refresh'}
        </Button>
      </div>
      {!hero ? (
        <EmptyState
          title="Nothing fits right now"
          body="Every venue is outside your limits. Loosen cover, line or distance."
          action={
            <Link className="text-accent underline" to="/onboarding">
              Edit prefs
            </Link>
          }
        />
      ) : (
        <PickHero rec={hero} onShare={() => void share()} />
      )}
      {rest.length > 0 && (
        <section aria-labelledby="also-good">
          <div className="mb-2 flex items-center justify-between">
            <h2 id="also-good" className="font-display text-base font-semibold">
              Also good
            </h2>
            <DemoBadge data={rest[0]} />
          </div>
          <ul className="space-y-2">
            {rest.slice(0, 4).map((r) => (
              <VenueCardCompact key={r.venue_id} rec={r} />
            ))}
          </ul>
        </section>
      )}
      {excluded.length > 0 && (
        <section>
          <button
            type="button"
            className="min-h-[44px] text-sm text-muted underline"
            aria-expanded={showExcluded}
            onClick={() => setShowExcluded((v) => !v)}
          >
            {showExcluded ? 'Hide' : 'Show'} {excluded.length} excluded
          </button>
          {showExcluded && (
            <ul className="mt-2 space-y-2">
              {excluded.map((r) => (
                <VenueCardCompact key={r.venue_id} rec={r} excluded />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
