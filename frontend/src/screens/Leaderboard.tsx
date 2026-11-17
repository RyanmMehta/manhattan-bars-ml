import { useState } from 'react';
import { useLeaderboard } from '../api/queries';
import type { LeaderboardRow } from '../api/types';
import { DemoBadge } from '../components/demo/DemoBadge';
import { Chip } from '../components/ui/Chip';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';
import { usePersona } from '../state/persona';

function Stars({ r }: { r: number }) {
  const n = Math.max(1, Math.min(5, Math.round(r * 5)));
  return (
    <span aria-label={`Reputation ${n} of 5`} className="text-warn">
      {'★'.repeat(n)}
      <span className="text-line">{'★'.repeat(5 - n)}</span>
    </span>
  );
}

function Row({ r, me }: { r: LeaderboardRow & { shownRank: number }; me: boolean }) {
  return (
    <li
      data-testid={me ? 'me-row' : 'lb-row'}
      className={`flex items-center gap-3 rounded-md border px-3 py-2 ${me ? 'border-accent bg-accent/10' : 'border-line bg-surface'}`}
    >
      <span className="w-7 text-right font-display text-base text-muted">{r.shownRank}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {r.display_name}
          {me ? ' (you)' : ''}
        </p>
        <p className="text-xs text-muted">
          Level {r.level} · <Stars r={r.reputation} />
        </p>
      </div>
      <span className="font-display text-base">{r.points}</span>
    </li>
  );
}

/** US-07: leaderboard. */
export function Leaderboard() {
  const q = useLeaderboard();
  const { token } = usePersona();
  const [tab, setTab] = useState<'week' | 'all'>('week');
  const me = token?.role === 'scout' ? token.id : 'syn-s-demo';

  if (q.isPending) return <Skeleton lines={6} className="h-12" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  if (!q.data.length) return <EmptyState title="No scouts yet" body="Send the first vibe check tonight." />;
  const sorted = [...q.data]
    .sort((a, b) => (tab === 'week' ? b.points_week - a.points_week : a.rank - b.rank))
    .map((r, i) => ({ ...r, shownRank: i + 1, points: tab === 'week' ? r.points_week : r.points }));
  const top = sorted.slice(0, 20);
  const mine = sorted.find((r) => r.scout_id === me);
  const pinned = mine && mine.shownRank > 20 ? mine : null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold">Scout leaderboard</h1>
        <DemoBadge data={q.data[0]} />
      </div>
      <div className="flex gap-2" role="tablist">
        <Chip role="tab" aria-selected={tab === 'week'} selected={tab === 'week'} onClick={() => setTab('week')}>
          This week
        </Chip>
        <Chip role="tab" aria-selected={tab === 'all'} selected={tab === 'all'} onClick={() => setTab('all')}>
          All time
        </Chip>
      </div>
      <ol className="space-y-1.5">
        {top.map((r) => (
          <Row key={r.scout_id} r={r} me={r.scout_id === me} />
        ))}
      </ol>
      {pinned && (
        <div>
          <p className="py-1 text-center text-xs text-muted">⋯</p>
          <ol>
            <Row r={pinned} me />
          </ol>
        </div>
      )}
    </div>
  );
}
