import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { configureClient } from '../api/client';
import { env } from '../config/env';

const KEY = 'na.now.v1';
interface ClockCtx {
  now: string | null;
  setNow: (iso: string | null) => void;
}
const Ctx = createContext<ClockCtx | null>(null);

function readStored(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** `now` precedence (OUTLINE §4): URL ?now= > demo panel > VITE_DEMO_NOW > health.demo_now. */
export function DemoClockProvider({ children, healthNow }: { children: ReactNode; healthNow?: string | null }) {
  const [params, setParams] = useSearchParams();
  const urlNow = params.get('now');
  const [panelNow, setPanelNow] = useState<string | null>(readStored);
  const now = urlNow ?? panelNow ?? env.demoNow ?? healthNow ?? null;

  // Keep the API client in sync synchronously so the first fetch already carries `now`.
  configureClient({ now: () => now });
  useEffect(() => {
    configureClient({ now: () => now });
  }, [now]);

  const setNow = useCallback((iso: string | null) => {
    try {
      if (iso) sessionStorage.setItem(KEY, iso);
      else sessionStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
    setPanelNow(iso);
    // A URL ?now= outranks the panel, so keep it in step when the presenter time-travels.
    setParams(
      (p) => {
        if (!p.has('now')) return p;
        const n = new URLSearchParams(p);
        if (iso) n.set('now', iso);
        else n.delete('now');
        return n;
      },
      { replace: true },
    );
  }, [setParams]);
  const value = useMemo(() => ({ now, setNow }), [now, setNow]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDemoClock(): ClockCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useDemoClock outside DemoClockProvider');
  return c;
}
/** `now` for display maths, falling back to the real clock. */
export function useNowIso(): string {
  const { now } = useDemoClock();
  return now ?? new Date().toISOString();
}
