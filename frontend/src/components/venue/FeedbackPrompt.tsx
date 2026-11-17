import { useState } from 'react';
import { ApiError, api } from '../../api/client';
import { usePersona } from '../../state/persona';
import { useToast } from '../ui/Toast';

/** T18 (stretch): post-visit feedback → POST /api/feedback. */
export function FeedbackPrompt({ venueId }: { venueId: string }) {
  const { ensureLogin, token } = usePersona();
  const toast = useToast();
  const [done, setDone] = useState(false);
  if (done) return <p className="text-sm text-muted">Thanks, that helps tomorrow’s picks.</p>;
  const send = async (visited: 0 | 1, rating: number | null) => {
    try {
      const t = token?.role === 'user' ? token : await ensureLogin('planner');
      await api.feedback({ user_id: t.id ?? undefined, venue_id: venueId, visited, rating });
      setDone(true);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Could not send feedback', 'error');
    }
  };
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">Went here tonight? How was it?</p>
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3, 4, 5].map((r) => (
          <button key={r} type="button" aria-label={`Rate ${r} of 5`} onClick={() => void send(1, r)}
            className="min-h-[44px] min-w-[44px] rounded-md border border-line bg-raised text-warn hover:border-warn">
            {'★'.repeat(r)}
          </button>
        ))}
        <button type="button" onClick={() => void send(0, null)} className="min-h-[44px] rounded-md border border-line px-3 text-sm text-muted">
          Didn’t go
        </button>
      </div>
    </div>
  );
}
