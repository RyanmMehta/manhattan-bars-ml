export function MissingList({ missing }: { missing: string[] }) {
  if (!missing.length) return null;
  return (
    <ul className="space-y-1 text-sm text-muted" aria-label="What we don’t know">
      {missing.map((m) => (
        <li key={m} className="flex gap-2"><span aria-hidden>?</span>{m}</li>
      ))}
    </ul>
  );
}
