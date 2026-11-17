import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { venueName } from '../api/adapters';
import { useSubmitReport, useVenues } from '../api/queries';
import type { ReportInput } from '../api/types';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { VibeCheckForm } from '../components/venue/VibeCheckForm';
import { PRESENCE_RADIUS_M } from '../config/thresholds';
import { haversineM, nearest } from '../lib/geo';
import { enqueue, flushQueue } from '../state/offlineQueue';
import { usePersona } from '../state/persona';
import { usePrefs } from '../state/prefs';

/** US-06: the 10-second vibe check. */
export function VibeCheck() {
  const [params] = useSearchParams();
  const { prefs } = usePrefs();
  const { persona, ownerVenueId } = usePersona();
  const toast = useToast();
  const nav = useNavigate();
  const [loc, setLoc] = useState<{ lat: number; lon: number } | null>(null);
  const venues = useVenues({ lat: prefs.lat, lon: prefs.lon });
  const submit = useSubmitReport(persona === 'planner' ? 'scout' : persona);
  const opened = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - opened.current) / 1000)), 250);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!('geolocation' in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (p) => setLoc({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => setLoc(null),
      { timeout: 3000, maximumAge: 60000 },
    );
  }, []);
  useEffect(() => {
    void flushQueue((i) => api.report(i)).then((r) => r.sent && toast(`Sent ${r.sent} queued vibe check(s)`));
  }, [toast]);

  const here = useMemo(() => loc ?? { lat: prefs.lat, lon: prefs.lon }, [loc, prefs.lat, prefs.lon]);
  const rows = useMemo(() => venues.data?.rows ?? [], [venues.data]);
  const near = useMemo(() => nearest(here, rows), [here, rows]);
  const preset = params.get('venue');
  const [chosen, setChosen] = useState<string | null>(null);
  const venueId = chosen ?? preset ?? (near && near.meters <= PRESENCE_RADIUS_M ? near.venue.venue_id : null);
  const venue = rows.find((v) => v.venue_id === venueId) ?? null;
  const dist = venue ? haversineM(here, venue) : null;
  const ownVenue = persona === 'owner' && venueId === ownerVenueId;

  const send = async (body: ReportInput) => {
    try {
      const r = await submit.mutateAsync(body);
      toast(`+${r.points_pending} pts pending · ${r.status} · ${elapsed}s`);
      nav(`/venue/${body.venue_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'network') {
        enqueue(body);
        toast('Offline: saved, will retry once', 'warn');
      } else {
        toast(e instanceof ApiError ? e.message : 'Could not send', 'error');
      }
    }
  };

  if (venues.isPending) return <Skeleton lines={3} className="h-24" />;
  if (venues.isError) return <ErrorState error={venues.error} onRetry={() => void venues.refetch()} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold">Vibe check</h1>
          <p className="text-xs text-muted">Ten seconds. Three taps.</p>
        </div>
        <span className="rounded-full border border-cyan px-3 py-1 font-display text-sm text-cyan" data-testid="vibe-timer" aria-label={`${elapsed} seconds since opening`}>
          {elapsed}s
        </span>
      </div>
      <Card className="space-y-2">
        <label className="text-sm font-medium" htmlFor="venue-pick">
          Venue
        </label>
        <select
          id="venue-pick"
          value={venueId ?? ''}
          onChange={(e) => setChosen(e.target.value || null)}
          className="min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm"
        >
          <option value="">Pick where you are…</option>
          {rows.map((v) => (
            <option key={v.venue_id} value={v.venue_id}>
              {venueName(v)}
              {v.distance_km !== undefined && v.distance_km !== null ? ` · ${v.distance_km.toFixed(1)} km` : ''}
            </option>
          ))}
        </select>
        {venue && (
          <p className="text-xs" data-testid="presence-hint">
            {dist !== null && dist <= PRESENCE_RADIUS_M ? (
              <span className="text-cyan">You look nearby</span>
            ) : (
              <span className="text-warn">Not verified: you seem &gt; {PRESENCE_RADIUS_M} m away (the server decides)</span>
            )}
          </p>
        )}
      </Card>
      {ownVenue ? (
        <Card>
          <p className="text-sm">Owners can’t report their own venue.</p>
          <Link className="text-sm text-accent underline" to={`/owner/${ownerVenueId}`}>
            Post an official update instead
          </Link>
        </Card>
      ) : (
        <VibeCheckForm venueId={venueId} location={loc} busy={submit.isPending} onSubmit={(b) => void send(b)} />
      )}
      <div className="flex justify-between text-sm">
        <Link to="/scout/bounties" className="min-h-[44px] text-cyan">
          Open bounties →
        </Link>
        <Link to="/scout/leaderboard" className="min-h-[44px] text-cyan">
          Leaderboard →
        </Link>
      </div>
      <p className="text-xs text-muted">
        Points are calculated on the server. <DemoBadge force />
      </p>
    </div>
  );
}
