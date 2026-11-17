import { lazy, Suspense, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { venueName } from '../api/adapters';
import { useOwnerDashboard, useOwnerUpdate, useVenue, useVenues } from '../api/queries';
import type { VenueUpdate } from '../api/types';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { OfferCard } from '../components/venue/OfferCard';
import { ReportTimeline } from '../components/venue/ReportTimeline';
import { GENRES, genreLabel } from '../config/genres';
import { shiftIso } from '../lib/time';
import { useNowIso } from '../state/demoClock';
import { usePersona } from '../state/persona';

const DemandChart = lazy(() => import('../components/owner/DemandChart'));

type Draft = Omit<VenueUpdate, 'update_id' | 'ts' | 'venue_id'>;

/** US-09: owner dashboard. SYNTHETIC: KPIs come from GET /api/owner/{id}/dashboard, synthetic until backend analytics exist. */
export function OwnerDashboard() {
  const { venueId = '' } = useParams();
  const nav = useNavigate();
  const now = useNowIso();
  const dash = useOwnerDashboard(venueId);
  const detail = useVenue(venueId);
  const all = useVenues({});
  const upd = useOwnerUpdate(venueId);
  const { login, token } = usePersona();
  const toast = useToast();
  const [d, setD] = useState<Draft>({ cover_usd: 10, dj: '', genres: [], event: '', offer: '', offer_expires_at: null });
  const [expires, setExpires] = useState<'none' | 'midnight' | '1h'>('midnight');

  const draft: Draft = {
    ...d,
    dj: d.dj || null,
    event: d.event || null,
    offer: d.offer || null,
    offer_expires_at: expires === 'none' ? null : expires === '1h' ? shiftIso(now, 60) : '2026-11-15T00:00:00-05:00',
  };

  const post = async () => {
    try {
      if (!(token?.role === 'owner' && token.venue_id === venueId)) await login('owner', venueId);
      await upd.mutateAsync(draft);
      toast('Update posted. Guests see it on your card now.');
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Could not post update', 'error');
    }
  };

  const name = detail.data ? venueName(detail.data.venue) : 'Your venue';
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent">Owner dashboard</p>
          <h1 className="font-display text-xl font-semibold">{name}</h1>
        </div>
        <label className="text-xs text-muted">
          Venue
          <select
            value={venueId}
            onChange={(e) => nav(`/owner/${e.target.value}`)}
            className="ml-2 min-h-[44px] rounded-md border border-line bg-surface px-2 text-sm text-ink"
          >
            {(all.data?.rows ?? []).map((v) => (
              <option key={v.venue_id} value={v.venue_id}>
                {venueName(v)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          {dash.isPending ? (
            <Skeleton lines={2} className="h-24" />
          ) : dash.isError ? (
            <ErrorState error={dash.error} onRetry={() => void dash.refetch()} />
          ) : (
            <Card className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-base font-semibold">Tonight</h2>
                <DemoBadge data={dash.data} />
              </div>
              <dl className="grid grid-cols-3 gap-2 lg:grid-cols-5" data-testid="kpis">
                {(
                  [
                    ['Views', dash.data.views],
                    ['Taps', dash.data.taps],
                    ['Saves', dash.data.saves],
                    ['Reports', dash.data.reports_tonight],
                    ['In picks', dash.data.rec_appearances],
                  ] as const
                ).map(([k, v]) => (
                  <div key={k} className="rounded-md bg-raised p-3">
                    <dt className="text-xs text-muted">{k}</dt>
                    <dd className="font-display text-xl">{v}</dd>
                  </div>
                ))}
              </dl>
              <h3 className="text-sm font-medium">Demand by hour</h3>
              <Suspense fallback={<Skeleton className="h-48" />}>
                <DemandChart data={dash.data.demand_by_hour} />
              </Suspense>
            </Card>
          )}
          <Card>
            <h2 className="mb-2 font-display text-base font-semibold">Recent scout reports</h2>
            {detail.data ? <ReportTimeline reports={detail.data.recent_reports} now={now} /> : <Skeleton className="h-16" />}
          </Card>
        </div>
        <Card className="space-y-3">
          <h2 className="font-display text-base font-semibold">Post an update</h2>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-muted">
              Cover ($)
              <input
                type="number"
                min={0}
                value={d.cover_usd ?? ''}
                onChange={(e) => setD({ ...d, cover_usd: e.target.value === '' ? null : Number(e.target.value) })}
                className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
              />
            </label>
            <label className="text-xs text-muted">
              DJ
              <input
                value={d.dj ?? ''}
                onChange={(e) => setD({ ...d, dj: e.target.value })}
                className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
              />
            </label>
          </div>
          <label className="block text-xs text-muted">
            Offer
            <input
              value={d.offer ?? ''}
              placeholder="e.g. $10 cover before midnight"
              onChange={(e) => setD({ ...d, offer: e.target.value })}
              className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink placeholder:text-muted"
            />
          </label>
          <label className="block text-xs text-muted">
            Event
            <input
              value={d.event ?? ''}
              onChange={(e) => setD({ ...d, event: e.target.value })}
              className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
            />
          </label>
          <label className="block text-xs text-muted">
            Music tonight
            <select
              multiple
              value={Array.isArray(d.genres) ? d.genres : []}
              onChange={(e) => setD({ ...d, genres: Array.from(e.target.selectedOptions).map((o) => o.value) })}
              className="mt-1 h-24 w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
            >
              {GENRES.map((g) => (
                <option key={g} value={g}>
                  {genreLabel(g)}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-muted">
            Offer expires
            <select
              value={expires}
              onChange={(e) => setExpires(e.target.value as typeof expires)}
              className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
            >
              <option value="midnight">At midnight</option>
              <option value="1h">In 1 hour</option>
              <option value="none">No expiry</option>
            </select>
          </label>
          <div>
            <p className="mb-1 text-xs text-muted">Preview: how guests see it</p>
            <OfferCard u={{ ...draft, venue_id: venueId, is_synthetic: 1 }} />
          </div>
          <Button className="w-full" onClick={() => void post()} disabled={upd.isPending}>
            {upd.isPending ? 'Posting…' : 'Post update'}
          </Button>
        </Card>
      </div>
    </div>
  );
}
