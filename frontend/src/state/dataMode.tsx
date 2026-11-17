import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { onDataHeader } from '../api/client';
import type { DataHeader, Health } from '../api/types';
import type { ApiMode } from '../config/env';

interface DataCtx {
  mode: ApiMode;
  health: Health | null;
  dataHeader: DataHeader;
  /** True when the global "demo data" banner must show (RULES §4.3). */
  synthetic: boolean;
}
const Ctx = createContext<DataCtx>({ mode: 'mock', health: null, dataHeader: null, synthetic: true });

export function DataModeProvider({ mode, health, children }: { mode: ApiMode; health: Health | null; children: ReactNode }) {
  const [dataHeader, setHeader] = useState<DataHeader>(null);
  useEffect(() => onDataHeader(setHeader), []);
  const value = useMemo(() => {
    const syn = mode === 'mock' || dataHeader === 'synthetic' || dataHeader === 'mixed' || health?.data === 'synthetic' || health?.data === 'mixed';
    return { mode, health, dataHeader, synthetic: syn };
  }, [mode, health, dataHeader]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export const useDataMode = () => useContext(Ctx);
