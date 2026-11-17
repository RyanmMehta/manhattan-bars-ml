export function Skeleton({ className = '', lines = 1 }: { className?: string; lines?: number }) {
  return (
    <div role="status" aria-label="Loading" className="space-y-2">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={`animate-pulse rounded-md bg-raised ${className || 'h-24'}`} />
      ))}
    </div>
  );
}
