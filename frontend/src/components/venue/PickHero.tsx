import { Link } from 'react-router-dom';
import { displayBand } from '../../api/adapters';
import type { Recommendation } from '../../api/types';
import { DemoBadge } from '../demo/DemoBadge';
import { FreshnessTag } from './FreshnessTag';
import { MissingList } from './MissingList';
import { ReasonList } from './ReasonList';
import { ScoreTriplet } from './ScoreTriplet';

export function PickHero({ rec, onShare }: { rec: Recommendation; onShare?: () => void }) {
  const band = displayBand(rec);
  return (
    <article data-testid="pick-hero" className="rounded-lg border border-accent/50 bg-surface p-4" aria-labelledby="pick-name">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">Tonight’s pick</p>
          <h2 id="pick-name" className="font-display text-xl font-semibold">{rec.name}</h2>
          <p className="text-sm text-muted">
            {rec.distance_km !== null ? `${rec.distance_km.toFixed(1)} km away` : 'distance unknown'}
            {rec.cluster_label ? ` · ${rec.cluster_label}` : ''}
          </p>
        </div>
        <DemoBadge data={rec} />
      </div>
      <div className="mt-3"><ScoreTriplet match={rec.match_score} vibe={rec.vibe_score} confidence={rec.confidence} display={rec.display} /></div>
      <div className="mt-2">{rec.freshness_minutes !== undefined && <FreshnessTag minutes={rec.freshness_minutes} nReports={rec.n_reports} />}</div>
      <div className="mt-3 space-y-2">
        <ReasonList reasons={rec.reasons.slice(0, 4)} />
        <MissingList missing={rec.missing} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to={`/venue/${rec.venue_id}`} className="inline-flex min-h-[44px] flex-1 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-bg">
          Open venue
        </Link>
        {onShare && (
          <button type="button" onClick={onShare} className="inline-flex min-h-[44px] items-center rounded-md border border-line bg-raised px-4 text-sm">Share pick</button>
        )}
        {band === 'none' && (
          <Link to={`/scout?venue=${rec.venue_id}`} className="inline-flex min-h-[44px] items-center rounded-md border border-cyan px-4 text-sm text-cyan">Be the Scout</Link>
        )}
      </div>
    </article>
  );
}
