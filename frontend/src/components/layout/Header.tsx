import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { genreLabel } from '../../config/genres';
import { usePersona } from '../../state/persona';
import { usePrefs } from '../../state/prefs';

export function Header({ onSecret }: { onSecret: () => void }) {
  const { prefs, fromUrl } = usePrefs();
  const { persona } = usePersona();
  const taps = useRef<number[]>([]);
  const tap = () => {
    const t = Date.now();
    taps.current = [...taps.current.filter((x) => t - x < 2000), t];
    if (taps.current.length >= 5) { taps.current = []; onSecret(); }
  };
  const summary = prefs.genres.length ? prefs.genres.slice(0, 2).map(genreLabel).join(' + ') : 'Any music';
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/95 backdrop-blur">
      <div className="mx-auto flex max-w-[560px] items-center justify-between gap-2 px-4 py-2">
        <button type="button" onClick={tap} className="flex min-h-[44px] items-center gap-2" aria-label="Nightlife Autopilot (tap 5 times for demo panel)">
          <span aria-hidden className="h-6 w-6 rounded-full border-[3px] border-accent" />
          <span className="font-display text-base font-semibold">Nightlife<span className="text-accent">Autopilot</span></span>
        </button>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-raised px-2 py-1 text-[11px] uppercase tracking-wide text-muted" aria-label={`Persona: ${persona}`}>{persona}</span>
          <Link to="/onboarding" className="inline-flex min-h-[44px] items-center rounded-full border border-line px-3 text-xs" aria-label="Edit preferences">
            Prefs · {fromUrl ? 'shared' : summary}
          </Link>
        </div>
      </div>
    </header>
  );
}
