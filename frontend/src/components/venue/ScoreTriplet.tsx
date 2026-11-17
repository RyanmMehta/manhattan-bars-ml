import { displayBand, vibeLabel } from '../../api/adapters';
import type { Display } from '../../api/types';
import { ConfidenceMeter } from './ConfidenceMeter';

export function ScoreTriplet({ match, vibe, confidence, display }: { match: number; vibe: number | null; confidence: number | null; display?: Display }) {
  const band = displayBand({ vibe_score: vibe, confidence, display });
  return (
    <dl className="grid grid-cols-3 gap-2 text-center">
      <div className="rounded-md bg-raised p-2">
        <dt className="text-[11px] uppercase tracking-wide text-muted">Match</dt>
        <dd className="font-display text-xl font-semibold text-accent">{match}</dd>
      </div>
      <div className="rounded-md bg-raised p-2">
        <dt className="text-[11px] uppercase tracking-wide text-muted">Vibe</dt>
        <dd className={`font-display text-xl font-semibold ${band === 'show' ? 'text-ink' : 'text-muted'}`}>
          {band === 'none' || vibe === null ? '—' : Math.round(vibe)}
          <span className="block text-[11px] font-normal text-muted">{band === 'none' ? 'no fresh reports' : band === 'low' ? 'low confidence' : vibeLabel(vibe)}</span>
        </dd>
      </div>
      <div className="rounded-md bg-raised p-2">
        <dt className="text-[11px] uppercase tracking-wide text-muted">Confidence</dt>
        <dd className="mt-1 flex justify-center"><ConfidenceMeter confidence={confidence} /></dd>
      </div>
    </dl>
  );
}
