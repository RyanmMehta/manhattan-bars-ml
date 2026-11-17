import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { api, getToken, setToken, type StoredToken } from '../api/client';
import type { Role } from '../api/types';

export type Persona = 'planner' | 'scout' | 'owner';
const KEY = 'na.persona.v1';
// SYNTHETIC: demo persona names for demo-login; replace with real accounts once real login exists.
export const DEMO_NAMES: Record<Persona, string> = { planner: 'Demo Planner', scout: 'Demo Scout', owner: 'Demo Owner' };
const ROLE: Record<Persona, Role> = { planner: 'user', scout: 'scout', owner: 'owner' };
// SYNTHETIC: default owner venue for the demo script (Mehanata Bulgarian Bar).
export const DEMO_OWNER_VENUE = '0370-23-127248';

interface PersonaState {
  persona: Persona;
  ownerVenueId: string;
}
interface PersonaCtx extends PersonaState {
  token: StoredToken | null;
  login: (p: Persona, venueId?: string) => Promise<StoredToken>;
  ensureLogin: (p?: Persona) => Promise<StoredToken>;
  setPersona: (p: Persona) => void;
  logout: () => void;
}
const Ctx = createContext<PersonaCtx | null>(null);

function load(): PersonaState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const v = JSON.parse(raw) as Partial<PersonaState>;
      if (v.persona === 'planner' || v.persona === 'scout' || v.persona === 'owner') {
        return { persona: v.persona, ownerVenueId: v.ownerVenueId ?? DEMO_OWNER_VENUE };
      }
    }
  } catch {
    /* ignore */
  }
  return { persona: 'planner', ownerVenueId: DEMO_OWNER_VENUE };
}
function store(s: PersonaState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PersonaState>(load);
  const [token, setTok] = useState<StoredToken | null>(() => getToken());

  const login = useCallback(async (p: Persona, venueId?: string) => {
    const role = ROLE[p];
    const ownerVenueId = venueId ?? state.ownerVenueId;
    const res = await api.demoLogin({
      display_name: DEMO_NAMES[p],
      role,
      ...(role === 'owner' ? { venue_id: ownerVenueId } : {}),
    });
    const t: StoredToken = {
      token: res.token,
      issued_at: Date.now(),
      role,
      id: res.scout_id ?? res.user_id ?? null,
      venue_id: role === 'owner' ? ownerVenueId : null,
      display_name: DEMO_NAMES[p],
    };
    setToken(t);
    setTok(t);
    const next = { persona: p, ownerVenueId };
    store(next);
    setState(next);
    return t;
  }, [state.ownerVenueId]);

  const ensureLogin = useCallback(
    async (p?: Persona) => {
      const want = p ?? state.persona;
      const cur = getToken();
      if (cur && cur.role === ROLE[want]) return cur;
      return login(want);
    },
    [login, state.persona],
  );

  const setPersona = useCallback((p: Persona) => {
    setState((s) => {
      const n = { ...s, persona: p };
      store(n);
      return n;
    });
  }, []);
  const logout = useCallback(() => {
    setToken(null);
    setTok(null);
  }, []);

  const value = useMemo(
    () => ({ ...state, token, login, ensureLogin, setPersona, logout }),
    [state, token, login, ensureLogin, setPersona, logout],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePersona(): PersonaCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('usePersona outside PersonaProvider');
  return c;
}
