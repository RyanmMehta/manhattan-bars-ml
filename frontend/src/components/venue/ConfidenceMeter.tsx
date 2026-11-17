import { confidenceBars } from '../../api/adapters';

/** PRD §6: 4-bar meter + "Low/Some/Good/High". */
export function ConfidenceMeter({ confidence }: { confidence: number | null }) {
  const { bars, label } = confidenceBars(confidence);
  return (
    <span className="inline-flex items-center gap-1.5" aria-label={label ? `Confidence ${label} (${Math.round((confidence as number) * 100)}%)` : 'Confidence unknown'} role="img">
      <span className="flex items-end gap-0.5" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={`w-1.5 rounded-sm ${i <= bars ? 'bg-cyan' : 'bg-line'}`} style={{ height: `${4 + i * 3}px` }} />
        ))}
      </span>
      <span className="text-xs text-muted">{label ?? 'Unknown'}</span>
    </span>
  );
}
