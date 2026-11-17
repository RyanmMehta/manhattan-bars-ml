import { Link } from 'react-router-dom';
import { displayBand } from '../../api/adapters';
import type { Recommendation } from '../../api/types';
import { DemoBadge } from '../demo/DemoBadge';
import { ConfidenceMeter } from './ConfidenceMeter';
import { FreshnessTag } from './FreshnessTag';
import { VibeBadge } from './VibeBadge';

export function VenueCardCompact({ rec, excluded = false }: { rec: Recommendation; excluded?: boolean }) {
  const band = displayBand(rec);
  return (
    <li className={`rounded-lg border border-line bg-surface p-3 ${excluded ? 'opacity-60' : ''}`} data-testid={excluded ? 'excluded-card' : 'alt-card'}>
      <div className="flex items-start justify-between gap-2">
        <Link to={`/venue/${rec.venue_id}`} className="min-h-[44px] font-display text-base font-semibold hover:text-accent">
          {rec.rank ? <span className="mr-1 text-muted">#{rec.rank}</span> : null}{rec.name}
        </Link>
        <span className="font-display text-sm text-accent" aria-label={`Match ${rec.match_score}`}>{rec.match_score}<span className="text-xs text-muted"> match</span></span>
      </div>
      {excluded && rec.excluded_reason ? (
        <p className="text-sm text-muted">Excluded: {rec.excluded_reason}</p>
      ) : (
        <>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <VibeBadge vibe={rec.vibe_score} confidence={rec.confidence} display={rec.display} />
            <ConfidenceMeter confidence={rec.confidence} />
            <DemoBadge data={rec} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">{rec.freshness_minutes !== undefined && <FreshnessTag minutes={rec.freshness_minutes} />}
            {rec.reasons[0] && <span className="text-xs text-muted">· {rec.reasons[0]}</span>}</div>
          {band === 'none' && <Link to={`/scout?venue=${rec.venue_id}`} className="mt-1 inline-flex min-h-[44px] items-center text-sm text-cyan">Be the Scout →</Link>}
        </>
      )}
    </li>
  );
}
