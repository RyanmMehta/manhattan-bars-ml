import { isSynthetic } from '../../api/adapters';
import type { Synthetic } from '../../api/types';

/** CONTRACTS synthetic rule 5: a small "demo data" badge wherever synthetic data shows. */
export function DemoBadge({ data, force = false, className = '' }: { data?: { is_synthetic?: Synthetic } | null; force?: boolean; className?: string }) {
  if (!force && !isSynthetic(data)) return null;
  return (
    <span data-testid="demo-badge" title="Synthetic demo data — not real reports"
      className={`inline-flex shrink-0 items-center rounded-full border border-warn/60 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-warn ${className}`}>
      demo data
    </span>
  );
}
