import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
const V: Record<Variant, string> = {
  primary: 'bg-accent text-bg font-semibold hover:brightness-110',
  secondary: 'bg-raised text-ink border border-line hover:border-muted',
  ghost: 'text-ink hover:bg-raised',
  danger: 'bg-danger text-bg font-semibold',
};
export function Button({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...p}
      className={`inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md px-4 text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${V[variant]} ${className}`}
    />
  );
}
