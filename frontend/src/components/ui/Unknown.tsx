/** Null means unknown (RULES §3). */
export function Unknown({ label = 'not reported' }: { label?: string }) {
  return <span className="italic text-muted">{label}</span>;
}
