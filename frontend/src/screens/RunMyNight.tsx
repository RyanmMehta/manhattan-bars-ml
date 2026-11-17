import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePlan } from '../api/queries';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Button } from '../components/ui/Button';
import { Chip } from '../components/ui/Chip';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { ConfidenceMeter } from '../components/venue/ConfidenceMeter';
import { VibeBadge } from '../components/venue/VibeBadge';
import { env } from '../config/env';
import { clockLabel } from '../lib/time';
import type { PlanStop } from '../api/types';
import { usePrefs } from '../state/prefs';

function RouteMini({ stops }: { stops: PlanStop[] }) {
  if (stops.length < 2) return null;
  const lats = stops.map((s) => s.lat);
  const lons = stops.map((s) => s.lon);
  const pad = 0.0015;
  const [a, b] = [Math.min(...lats) - pad, Math.max(...lats) + pad];
  const [c, d] = [Math.min(...lons) - pad, Math.max(...lons) + pad];
  const x = (lon: number) => ((lon - c) / (d - c)) * 300;
  const y = (lat: number) => 140 - ((lat - a) / (b - a)) * 140;
  return (
    <svg viewBox="0 0 300 140" className="h-36 w-full rounded-md bg-raised" role="img" aria-label="Straight-line route between stops">
      <polyline points={stops.map((s) => `${x(s.lon)},${y(s.lat)}`).join(' ')} fill="none" stroke="var(--c-cyan)" strokeWidth={2} strokeDasharray="5 4" />
      {stops.map((s) => (
        <g key={s.venue_id}>
          <circle cx={x(s.lon)} cy={y(s.lat)} r={10} fill="var(--c-accent)" />
          <text x={x(s.lon)} y={y(s.lat) + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--c-bg)">
            {s.order}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** US-08 (stretch): Run My Night timeline + swap stop. */
export function RunMyNight() {
  const { prefs } = usePrefs();
  const [n, setN] = useState(3);
  const [exclude, setExclude] = useState<string[]>([]);
  const q = usePlan({ ...prefs, exclude_venue_ids: exclude, dwell_minutes: 60, max_total_walk_minutes: 30 }, n, env.featureRouting);

  if (!env.featureRouting) return <EmptyState title="Run My Night is coming soon" body="Enable VITE_FEATURE_ROUTING=1 to try it." />;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold">Run my night</h1>
        <DemoBadge data={q.data?.[0]} />
      </div>
      <div className="flex gap-2" role="group" aria-label="Number of stops">
        {[2, 3, 4].map((k) => (
          <Chip key={k} selected={n === k} onClick={() => setN(k)}>
            {k} stops
          </Chip>
        ))}
        {exclude.length > 0 && (
          <Button variant="ghost" onClick={() => setExclude([])}>
            Reset swaps
          </Button>
        )}
      </div>
      {q.isPending ? (
        <Skeleton lines={3} className="h-28" />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => void q.refetch()} />
      ) : !q.data.length ? (
        <EmptyState title="No plan fits" body="Loosen your limits and try again." />
      ) : (
        <>
          <RouteMini stops={q.data} />
          <ol className="relative space-y-3 border-l-2 border-line pl-4" aria-label="Plan">
            {q.data.map((s) => (
              <li key={s.venue_id} className="relative" data-testid="plan-stop">
                <span className="absolute -left-[27px] top-3 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[11px] font-bold text-bg">
                  {s.order}
                </span>
                {s.walk_minutes_from_prev !== null && (
                  <p className="mb-1 text-xs text-muted">
                    🚶 {s.walk_minutes_from_prev} min walk{s.distance_km !== null ? ` · ${s.distance_km.toFixed(1)} km` : ''}
                  </p>
                )}
                <div className="rounded-lg border border-line bg-surface p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs text-cyan">
                        {clockLabel(s.arrive_at)} – {clockLabel(s.leave_at)}
                      </p>
                      <Link to={`/venue/${s.venue_id}`} className="font-display text-base font-semibold hover:text-accent">
                        {s.name}
                      </Link>
                    </div>
                    <span className="font-display text-accent">{s.match_score}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <VibeBadge vibe={s.expected_vibe} confidence={s.confidence} />
                    <ConfidenceMeter confidence={s.confidence} />
                  </div>
                  {s.reasons.length > 0 && <p className="mt-1 text-xs text-muted">{s.reasons.join(' · ')}</p>}
                  <Button variant="ghost" className="mt-1 px-0 text-cyan" onClick={() => setExclude((e) => [...e, s.venue_id])}>
                    Swap stop
                  </Button>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
