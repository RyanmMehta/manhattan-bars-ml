import { Link } from 'react-router-dom';
import { useBounties } from '../api/queries';
import { DemoBadge } from '../components/demo/DemoBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { countdown } from '../lib/time';
import { useNowIso } from '../state/demoClock';

/** US-07 AC2: open bounties; tap → vibe check for that venue. */
export function Bounties() {
  const q = useBounties();
  const now = useNowIso();
  if (q.isPending) return <Skeleton lines={4} className="h-20" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold">Open bounties</h1>
        <DemoBadge data={q.data[0]} />
      </div>
      <p className="text-sm text-muted">Venues we know least about right now. The first good report claims it.</p>
      {!q.data.length ? (
        <EmptyState title="No open bounties" body="Every venue has fresh reports. Nice work." />
      ) : (
        <ul className="space-y-2">
          {[...q.data]
            .sort((a, b) => b.points - a.points)
            .map((b) => (
              <li key={b.bounty_id}>
                <Link
                  to={`/scout?venue=${b.venue_id}`}
                  data-testid="bounty"
                  className="flex items-center gap-3 rounded-lg border border-line bg-surface p-3 hover:border-cyan"
                >
                  <span className="flex h-12 w-14 shrink-0 flex-col items-center justify-center rounded-md bg-cyan/15 font-display text-lg text-cyan">
                    {b.points}
                    <span className="text-[10px] uppercase">pts</span>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{b.venue_name}</span>
                    <span className="block text-xs text-muted">{b.reason}</span>
                  </span>
                  <span className="text-right text-xs text-warn">{countdown(b.expires_at, now) ?? 'open'}</span>
                </Link>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
