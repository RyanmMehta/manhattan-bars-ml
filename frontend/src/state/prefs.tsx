import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Preferences } from '../api/types';
import { decodePrefs } from '../lib/share';
import { loadPrefs, savePrefs } from './prefsReducer';

interface PrefsCtx {
  /** Effective prefs for this view: URL ?prefs= overrides stored prefs (never saved). */
  prefs: Preferences;
  stored: Preferences;
  saved: boolean;
  fromUrl: boolean;
  save: (p: Preferences) => void;
}
const Ctx = createContext<PrefsCtx | null>(null);

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [{ prefs: stored, saved }, setState] = useState(loadPrefs);
  const [params] = useSearchParams();
  const urlPrefs = useMemo(() => decodePrefs(params.get('prefs')), [params]);
  const save = useCallback((p: Preferences) => {
    savePrefs(p);
    setState({ prefs: p, saved: true });
  }, []);
  const value = useMemo<PrefsCtx>(
    () => ({ prefs: urlPrefs ?? stored, stored, saved, fromUrl: !!urlPrefs, save }),
    [urlPrefs, stored, saved, save],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePrefs(): PrefsCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('usePrefs outside PrefsProvider');
  return c;
}
