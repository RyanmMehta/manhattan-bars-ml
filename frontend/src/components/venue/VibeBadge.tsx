import { displayBand, vibeLabel } from '../../api/adapters';
import type { Display } from '../../api/types';

const COLOR = { Chill: 'border-chill text-chill', Lively: 'border-lively text-lively', Packed: 'border-packed text-packed' } as const;

/** Vibe number + band label; colour is never the only cue (RULES §3). */
export function VibeBadge({ vibe, confidence, display, size = 'md' }: { vibe: number | null; confidence: number | null; display?: Display; size?: 'md' | 'lg' }) {
  const band = displayBand({ vibe_score: vibe, confidence, display });
  const label = vibeLabel(vibe);
  if (band === 'none' || vibe === null || !label) {
    return (
      <span data-testid="vibe-badge" data-band="none" className="inline-flex items-center gap-1 rounded-md border border-none px-2 py-1 text-xs text-muted">
        No fresh reports
      </span>
    );
  }
  const low = band === 'low';
  return (
    <span data-testid="vibe-badge" data-band={band} aria-label={`Vibe ${Math.round(vibe)} of 100, ${label}${low ? ', low confidence' : ''}`}
      className={`inline-flex items-baseline gap-1.5 rounded-md border px-2 py-1 ${low ? 'border-line text-muted' : COLOR[label]}`}>
      <span className={`font-display font-semibold ${size === 'lg' ? 'text-xl' : 'text-base'}`}>{Math.round(vibe)}</span>
      <span className="text-xs font-medium">{label}</span>
      {low && <span className="text-[11px] italic">low confidence</span>}
    </span>
  );
}
