import { useState } from 'react';
import type { ReportInput } from '../../api/types';
import { GENRES, genreLabel } from '../../config/genres';
import { REPORT_LINE_CHIPS } from '../../config/thresholds';
import { Button } from '../ui/Button';
import { Chip } from '../ui/Chip';

const CROWD = ['Empty', 'Quiet', 'Buzzing', 'Busy', 'Packed'];
const DANCE = ['None', 'Some', 'Lots'];

/** US-06: the 10-second vibe check body. The server sets scout_id, ts, verified_presence. */
export function VibeCheckForm({
  venueId,
  location,
  busy = false,
  onSubmit,
}: {
  venueId: string | null;
  location: { lat: number; lon: number } | null;
  busy?: boolean;
  onSubmit: (body: ReportInput) => void;
}) {
  const [crowd, setCrowd] = useState<number | null>(null);
  const [dancing, setDancing] = useState<number | null>(null);
  const [line, setLine] = useState<number | null>(null);
  const [more, setMore] = useState(false);
  const [cover, setCover] = useState<string>('');
  const [genre, setGenre] = useState<string>('');
  const ready = venueId !== null && crowd !== null && dancing !== null && line !== null;

  const submit = () => {
    if (!ready) return;
    const body: ReportInput = { venue_id: venueId, crowd, dancing, line_minutes: line };
    if (cover !== '') body.cover_usd = Number(cover);
    if (genre) body.music_genre = genre;
    if (location) {
      body.lat = location.lat;
      body.lon = location.lon;
    }
    onSubmit(body);
  };

  return (
    <form
      className="space-y-4"
      aria-label="Vibe check"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <fieldset>
        <legend className="text-sm font-medium">How full is it?</legend>
        <div className="mt-2 grid grid-cols-5 gap-1.5">
          {CROWD.map((c, i) => (
            <button
              key={c}
              type="button"
              aria-pressed={crowd === i + 1}
              aria-label={`Crowd ${i + 1}: ${c}`}
              onClick={() => setCrowd(i + 1)}
              className={`flex min-h-[64px] flex-col items-center justify-center rounded-md border text-xs ${
                crowd === i + 1 ? 'border-accent bg-accent/20 text-ink' : 'border-line bg-surface text-muted'
              }`}
            >
              <span className="font-display text-xl text-ink">{i + 1}</span>
              {c}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="text-sm font-medium">Dancing?</legend>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {DANCE.map((d, i) => (
            <Chip key={d} selected={dancing === i} onClick={() => setDancing(i)} className="justify-center">
              {d}
            </Chip>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="text-sm font-medium">Line (minutes)</legend>
        <div className="mt-2 grid grid-cols-5 gap-1.5">
          {REPORT_LINE_CHIPS.map((l) => (
            <Chip key={l} selected={line === l} onClick={() => setLine(l)} className="justify-center px-1">
              {l === 30 ? '30+' : l}
            </Chip>
          ))}
        </div>
      </fieldset>
      <div>
        <button type="button" className="min-h-[44px] text-sm text-muted underline" aria-expanded={more} onClick={() => setMore((v) => !v)}>
          {more ? 'Hide' : 'Add'} cover & music (optional)
        </button>
        {more && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="text-xs text-muted">
              Cover ($)
              <input
                type="number"
                min={0}
                inputMode="numeric"
                value={cover}
                onChange={(e) => setCover(e.target.value)}
                className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
              />
            </label>
            <label className="text-xs text-muted">
              Music
              <select
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                className="mt-1 min-h-[44px] w-full rounded-md border border-line bg-surface px-2 text-sm text-ink"
              >
                <option value="">Not sure</option>
                {GENRES.map((g) => (
                  <option key={g} value={g}>
                    {genreLabel(g)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>
      <Button type="submit" className="w-full text-base" disabled={!ready || busy}>
        {busy ? 'Sending…' : 'Send vibe check'}
      </Button>
    </form>
  );
}
