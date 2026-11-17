export function ReasonList({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;
  return (
    <ul className="space-y-1 text-sm" aria-label="Why it fits">
      {reasons.map((r) => (
        <li key={r} className="flex gap-2"><span aria-hidden className="text-cyan">✓</span>{r}</li>
      ))}
    </ul>
  );
}
