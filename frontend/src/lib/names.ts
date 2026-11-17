/** PRD F6: fallback cleaner for SLA legal names when display_name is null. */
export function cleanVenueName(raw: string): string {
  const s = raw
    .replace(/\s+/g, ' ')
    .replace(/[,\s]*\b(LLC|INC|CORP|CORPORATION|LTD)\b\.?/gi, '')
    .replace(/["]/g, '')
    .trim();
  if (s && s === s.toUpperCase()) {
    return s
      .toLowerCase()
      .replace(/(^|[\s\-/&(])([a-z])/g, (_m, p: string, c: string) => p + c.toUpperCase())
      .replace(/'S\b/g, "'s");
  }
  return s;
}
