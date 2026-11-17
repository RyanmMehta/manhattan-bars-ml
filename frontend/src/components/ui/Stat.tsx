import type { ReactNode } from 'react';

export function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-md bg-raised p-3">
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 font-display text-base">{children}</dd>
    </div>
  );
}
