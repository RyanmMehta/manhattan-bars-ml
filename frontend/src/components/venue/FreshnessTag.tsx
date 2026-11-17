import { isStale } from '../../api/adapters';
import { agoLabel } from '../../lib/time';

export function FreshnessTag({ minutes, nReports }: { minutes: number | null; nReports?: number | null }) {
  if (minutes === null) return <span className="text-xs italic text-muted">no recent reports</span>;
  const stale = isStale(minutes);
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      {nReports !== undefined && nReports !== null && <span>{nReports} report{nReports === 1 ? '' : 's'},</span>}
      <span>updated {agoLabel(minutes)}</span>
      {stale && <span data-testid="stale-tag" className="rounded-full border border-warn/60 px-1.5 text-[11px] font-semibold text-warn">stale</span>}
    </span>
  );
}
