import { ApiError } from '../../api/client';
import { Button } from './Button';

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof ApiError ? error.message : 'Something went wrong loading this.';
  return (
    <div role="alert" className="rounded-lg border border-danger/50 bg-surface p-6 text-center">
      <p className="font-display text-lg">Couldn’t load this</p>
      <p className="mt-1 text-sm text-muted">{msg}</p>
      {onRetry && <Button variant="secondary" className="mt-4" onClick={onRetry}>Retry</Button>}
    </div>
  );
}
