import type { ReportInput } from '../api/types';

// PRD US-06 AC5: failed submits are queued in localStorage and retried once.
const KEY = 'na.reportQueue.v1';
export interface Queued {
  input: ReportInput;
  queued_at: number;
  attempts: number;
}

export function readQueue(): Queued[] {
  try {
    const v: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    return Array.isArray(v) ? (v as Queued[]) : [];
  } catch {
    return [];
  }
}
function write(q: Queued[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(q));
  } catch {
    /* ignore */
  }
}
export function enqueue(input: ReportInput, at = Date.now()) {
  write([...readQueue(), { input, queued_at: at, attempts: 0 }]);
}
/** Retry every queued report once; drop it after the retry whatever happens. */
export async function flushQueue(send: (i: ReportInput) => Promise<unknown>): Promise<{ sent: number; dropped: number }> {
  const q = readQueue();
  write([]);
  let sent = 0;
  let dropped = 0;
  for (const item of q) {
    try {
      await send(item.input);
      sent++;
    } catch {
      if (item.attempts < 1) write([...readQueue(), { ...item, attempts: item.attempts + 1 }]);
      else dropped++;
    }
  }
  return { sent, dropped };
}
