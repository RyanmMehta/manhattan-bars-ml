import type { ButtonHTMLAttributes } from 'react';

export function Chip({ selected = false, className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      {...p}
      className={`inline-flex min-h-[44px] items-center rounded-full border px-4 text-sm transition ${
        selected ? 'border-accent bg-accent/15 text-ink' : 'border-line bg-surface text-muted hover:text-ink'
      } ${className}`}
    />
  );
}
