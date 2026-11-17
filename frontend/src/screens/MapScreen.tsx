import { lazy, Suspense, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { venueName } from '../api/adapters';
import { useHeatmap, useVenues } from '../api/queries';
import { DemoBadge } from '../components/demo/DemoBadge';
import { ErrorState } from '../components/ui/ErrorState';
import { Sheet } from '../components/ui/Sheet';
import { Skeleton } from '../components/ui/Skeleton';
import { Toggle } from '../components/ui/Toggle';
import { VenueCard } from '../components/venue/VenueCard';
import { env } from '../config/env';
import { DEFAULT_DEMO_NOW } from '../config/thresholds';
import { clockLabel, shiftIso } from '../lib/time';
import { useDemoClock } from '../state/demoClock';

const MapView = lazy(() => import('../components/map/MapView'));
const START = '2026-11-14T20:00:00-05:00';

/** US-05: map + heat layer + time slider. */
export function MapScreen() {
  const { now, setNow } = useDemoClock();
  const [heat, setHeat] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const hm = useHeatmap(true);
  const venues = useVenues({});
  const names = useMemo(
    () => Object.fromEntries((venues.data?.rows ?? []).map((v) => [v.venue_id, venueName(v)])),
    [venues.data],
  );
  const selected = venues.data?.rows.find((v) => v.venue_id === sel) ?? null;
  const cur = now ?? DEFAULT_DEMO_NOW;
  const step = Math.max(0, Math.min(14, Math.round((Date.parse(cur) - Date.parse(START)) / (30 * 60e3))));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h1 className="font-display text-xl font-semibold">Where’s the energy?</h1>
        <DemoBadge data={hm.data?.[0]} />
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_320px]">
        <div className="relative h-[52vh] min-h-[320px] overflow-hidden rounded-lg border border-line bg-surface lg:h-[70vh]">
          {hm.isPending ? (
            <Skeleton className="h-full" />
          ) : hm.isError ? (
            <ErrorState error={hm.error} onRetry={() => void hm.refetch()} />
          ) : (
            <Suspense fallback={<Skeleton className="h-full" />}>
              <MapView points={hm.data} names={names} heat={heat} selected={sel} onSelect={setSel} />
            </Suspense>
          )}
          <div className="pointer-events-none absolute left-2 top-2 rounded-md bg-bg/85 px-2 py-1 text-[11px] text-muted" aria-hidden>
            <span className="text-chill">●</span> Chill <span className="text-lively">●</span> Lively{' '}
            <span className="text-packed">●</span> Packed <span>○</span> low confidence
          </div>
        </div>
        <div className="space-y-3">
          {env.featureHeatmap && (
            <div className="rounded-lg border border-line bg-surface px-4 py-1">
              <Toggle label="Heat" hint="Weighted by vibe × confidence" checked={heat} onChange={setHeat} />
            </div>
          )}
          <div className="rounded-lg border border-line bg-surface p-4">
            <label htmlFor="map-time" className="flex justify-between text-sm font-medium">
              Time <span className="font-display text-cyan">{clockLabel(cur)}</span>
            </label>
            <input
              id="map-time"
              type="range"
              min={0}
              max={14}
              value={step}
              aria-valuetext={clockLabel(cur)}
              onChange={(e) => setNow(shiftIso(START, Number(e.target.value) * 30))}
              className="mt-2 h-11 w-full accent-[var(--c-cyan)]"
            />
            <div className="flex justify-between text-xs text-muted">
              <span>8 PM</span>
              <span>Sat Nov 14 (demo)</span>
              <span>3 AM</span>
            </div>
          </div>
          {selected && (
            <div className="hidden lg:block">
              <ul>
                <VenueCard venue={selected} />
              </ul>
            </div>
          )}
        </div>
      </div>
      <div className="lg:hidden">
        <Sheet open={!!selected} onClose={() => setSel(null)} label="Selected venue">
          {selected && (
            <>
              <ul>
                <VenueCard venue={selected} />
              </ul>
              <Link
                to={`/venue/${selected.venue_id}`}
                className="mt-2 inline-flex min-h-[44px] w-full items-center justify-center rounded-md bg-accent text-sm font-semibold text-bg"
              >
                Open profile
              </Link>
            </>
          )}
        </Sheet>
      </div>
    </div>
  );
}
