import { useState } from 'react';
import { clockLabel, shiftIso } from '../../lib/time';
import { DEFAULT_DEMO_NOW } from '../../config/thresholds';
import { useDataMode } from '../../state/dataMode';
import { useDemoClock } from '../../state/demoClock';
import { usePersona, type Persona } from '../../state/persona';
import { Button } from '../ui/Button';
import { Chip } from '../ui/Chip';
import { Toggle } from '../ui/Toggle';
import { useToast } from '../ui/Toast';

const START = '2026-11-14T20:00:00-05:00';
/** US-10: hidden demo panel (?demo=1 or 5 taps on the logo). */
export function DemoPanel({ onClose }: { onClose: () => void }) {
  const { now, setNow } = useDemoClock();
  const { mode } = useDataMode();
  const { persona, login } = usePersona();
  const toast = useToast();
  const [outline, setOutline] = useState(() => document.documentElement.classList.contains('syn-outline'));
  const cur = now ?? DEFAULT_DEMO_NOW;
  const step = Math.round((Date.parse(cur) - Date.parse(START)) / (30 * 60e3));
  const switchPersona = async (p: Persona) => {
    try {
      await login(p);
      toast(`Logged in as demo ${p}`);
    } catch {
      toast('Demo login failed', 'error');
    }
  };
  const setMode = (m: 'mock' | 'live') => {
    try { sessionStorage.setItem('na.mode.v1', m); } catch { /* ignore */ }
    const u = new URL(window.location.href);
    u.searchParams.delete('mock');
    window.location.assign(u.toString());
  };
  return (
    <section aria-label="Demo panel" data-testid="demo-panel" className="mx-auto max-w-[560px] border-b border-cyan/40 bg-surface px-4 py-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-cyan">Demo panel</h2>
        <button type="button" onClick={onClose} className="min-h-[44px] min-w-[44px] text-muted" aria-label="Close demo panel">✕</button>
      </div>
      <p className="text-xs text-muted">Persona</p>
      <div className="mt-1 flex flex-wrap gap-2">
        {(['planner', 'scout', 'owner'] as Persona[]).map((p) => (
          <Chip key={p} selected={persona === p} onClick={() => void switchPersona(p)}>{p[0]!.toUpperCase() + p.slice(1)}</Chip>
        ))}
      </div>
      <label className="mt-3 block text-xs text-muted" htmlFor="demo-time">Time: <span className="font-display text-sm text-ink">{clockLabel(cur)}</span></label>
      <input id="demo-time" type="range" min={0} max={14} value={Math.max(0, Math.min(14, step))}
        onChange={(e) => setNow(shiftIso(START, Number(e.target.value) * 30))} className="h-11 w-full accent-[var(--c-cyan)]" aria-valuetext={clockLabel(cur)} />
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => setNow(shiftIso(cur, -60))}>−1 h</Button>
        <Button variant="secondary" onClick={() => setNow(DEFAULT_DEMO_NOW)}>Reset 11:30 PM</Button>
        <Button variant="secondary" onClick={() => setNow(shiftIso(cur, 60))}>+1 h</Button>
      </div>
      <p className="mt-3 text-xs text-muted">API mode</p>
      <div className="mt-1 flex gap-2">
        <Chip selected={mode === 'mock'} onClick={() => setMode('mock')}>Mock</Chip>
        <Chip selected={mode === 'live'} onClick={() => setMode('live')}>Live</Chip>
      </div>
      <div className="mt-2">
        <Toggle label="Show synthetic outline" checked={outline} onChange={(v) => { document.documentElement.classList.toggle('syn-outline', v); setOutline(v); }} />
      </div>
    </section>
  );
}
