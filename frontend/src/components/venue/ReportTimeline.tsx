import type { ScoutReport } from '../../api/types';
import { dancingLabel } from '../../api/adapters';
import { genreLabel } from '../../config/genres';
import { agoLabel, minutesAgo } from '../../lib/time';

export function ReportTimeline({ reports, now }: { reports: ScoutReport[]; now: string }) {
  if (!reports.length) return <p className="text-sm text-muted">No scout reports in the last 3 hours.</p>;
  return (
    <ol className="space-y-2" aria-label="Recent scout reports">
      {reports.map((r) => (
        <li key={r.report_id} className="flex items-start justify-between gap-2 border-l-2 border-line pl-3 text-sm">
          <div>
            <p className="text-xs text-muted">{agoLabel(minutesAgo(r.ts, now))}{r.scout_level ? ` · Level ${r.scout_level} scout` : ''}{r.verified_presence ? ' · verified' : ''}</p>
            <p>Crowd {r.crowd}/5 · Dancing {dancingLabel(r.dancing)} · Line {r.line_minutes} min{r.cover_usd !== null ? ` · $${r.cover_usd}` : ''}{r.music_genre ? ` · ${genreLabel(r.music_genre)}` : ''}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
