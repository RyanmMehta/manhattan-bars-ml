import { Link, useParams } from 'react-router-dom';
import { displayBand, venueName } from '../api/adapters';
import { useVenue } from '../api/queries';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { ConfidenceMeter } from '../components/venue/ConfidenceMeter';
import { FreshnessTag } from '../components/venue/FreshnessTag';
import { OfferCard } from '../components/venue/OfferCard';
import { ReportTimeline } from '../components/venue/ReportTimeline';
import { StateBlock } from '../components/venue/StateBlock';
import { VibeBadge } from '../components/venue/VibeBadge';
import { genreLabel, styleLabel } from '../config/genres';
import { directionsUrl } from '../lib/mapsLink';
import { shareUrl } from '../lib/share';
import { useDemoClock, useNowIso } from '../state/demoClock';
import { usePersona } from '../state/persona';
import { usePrefs } from '../state/prefs';

/** US-04: venue profile. */
export function VenueProfile() {
  const { venueId } = useParams();
  const q = useVenue(venueId);
  const nowIso = useNowIso();
  const { now } = useDemoClock();
  const { prefs } = usePrefs();
  const { persona, ownerVenueId } = usePersona();
  const toast = useToast();

  if (q.isPending) return <Skeleton lines={3} className="h-32" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  const { venue, state, recent_reports, offers } = q.data;
  const name = venueName(venue);
  const band = displayBand(state);
  const isOwnVenue = persona === 'owner' && ownerVenueId === venue.venue_id;

  const share = async () => {
    const url = shareUrl(`/venue/${venue.venue_id}`, now, prefs);
    try {
      await navigator.clipboard.writeText(url);
      toast('Link copied');
    } catch {
      toast(url, 'warn');
    }
  };

  return (
    <div className="space-y-4">
      <header>
        <div className="flex items-start justify-between gap-2">
          <h1 className="font-display text-xl font-semibold">{name}</h1>
          <DemoBadge data={venue} />
        </div>
        <p className="text-sm text-muted">{venue.address ?? `${venue.lat.toFixed(4)}, ${venue.lon.toFixed(4)}`}</p>
        <p className="text-sm text-muted">
          {styleLabel(venue.style)}
          {venue.price_level !== null ? ` · ${'$'.repeat(venue.price_level)}` : ''}
          {venue.genres.length ? ` · ${venue.genres.map(genreLabel).join(', ')}` : ''}
        </p>
      </header>

      <Card className="space-y-3" aria-labelledby="live-now">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="live-now" className="font-display text-base font-semibold">
            Live right now
          </h2>
          <DemoBadge data={state} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <VibeBadge vibe={state ? state.vibe_score : null} confidence={state ? state.confidence : null} display={state?.display} size="lg" />
          <ConfidenceMeter confidence={state ? state.confidence : null} />
          <FreshnessTag minutes={state ? state.freshness_minutes : null} nReports={state?.n_reports} />
        </div>
        <StateBlock s={state} />
        {band === 'none' && (
          <Link to={`/scout?venue=${venue.venue_id}`} className="inline-flex min-h-[44px] items-center text-sm text-cyan">
            No fresh reports. Be the Scout →
          </Link>
        )}
      </Card>

      {offers.length > 0 && (
        <section aria-labelledby="offers" className="space-y-2">
          <h2 id="offers" className="font-display text-base font-semibold">
            From the venue
          </h2>
          {offers.map((o, i) => (
            <OfferCard key={o.update_id ?? i} u={o} />
          ))}
        </section>
      )}

      <div className="grid grid-cols-2 gap-2">
        <a
          href={directionsUrl({ lat: venue.lat, lon: venue.lon, name })}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-bg"
          data-testid="directions"
        >
          Directions
        </a>
        <Button variant="secondary" onClick={() => void share()}>
          Share
        </Button>
        {!isOwnVenue && (
          <Link
            to={`/scout?venue=${venue.venue_id}`}
            className="col-span-2 inline-flex min-h-[44px] items-center justify-center rounded-md border border-cyan px-4 text-sm text-cyan"
          >
            Send vibe check
          </Link>
        )}
      </div>

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-display text-base font-semibold">Recent reports</h2>
          <DemoBadge data={recent_reports[0]} />
        </div>
        <ReportTimeline reports={recent_reports} now={nowIso} />
      </Card>

      {venue.complaint_risk !== null && (
        <Card>
          <h2 className="text-sm font-medium">311 noise-complaint risk</h2>
          <p className="text-sm text-muted">
            {Math.round(venue.complaint_risk * 100)}% (from NYC 311 public data; not a quality or vibe signal)
          </p>
        </Card>
      )}
    </div>
  );
}
