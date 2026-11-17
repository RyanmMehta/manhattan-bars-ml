import { GENRES, STYLES, genreLabel, styleLabel } from '../../config/genres';

export type SortKey = 'vibe' | 'distance' | 'name';
export interface FilterValue {
  q: string;
  style: string;
  genre: string;
  sort: SortKey;
}

/** US-03: search box + style/genre filters + sort. */
export function FilterBar({ value, onChange }: { value: FilterValue; onChange: (v: FilterValue) => void }) {
  const set = (patch: Partial<FilterValue>) => onChange({ ...value, ...patch });
  return (
    <div className="space-y-2" role="search">
      <label className="sr-only" htmlFor="venue-search">
        Search venues
      </label>
      <input
        id="venue-search"
        type="search"
        placeholder="Search bars, streets…"
        value={value.q}
        onChange={(e) => set({ q: e.target.value })}
        className="min-h-[44px] w-full rounded-md border border-line bg-surface px-3 text-sm placeholder:text-muted"
      />
      <div className="grid grid-cols-3 gap-2">
        <label className="text-xs text-muted">
          Style
          <select
            value={value.style}
            onChange={(e) => set({ style: e.target.value })}
            className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
          >
            <option value="">All styles</option>
            {STYLES.map((s) => (
              <option key={s} value={s}>
                {styleLabel(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          Genre
          <select
            value={value.genre}
            onChange={(e) => set({ genre: e.target.value })}
            className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
          >
            <option value="">All music</option>
            {GENRES.map((g) => (
              <option key={g} value={g}>
                {genreLabel(g)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          Sort
          <select
            value={value.sort}
            onChange={(e) => set({ sort: e.target.value as SortKey })}
            className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
          >
            <option value="vibe">Vibe</option>
            <option value="distance">Distance</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>
    </div>
  );
}
