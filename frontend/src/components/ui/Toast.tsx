import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type Tone = 'ok' | 'warn' | 'error';
interface ToastMsg { id: number; text: string; tone: Tone }
const Ctx = createContext<(text: string, tone?: Tone) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [list, setList] = useState<ToastMsg[]>([]);
  const push = useCallback((text: string, tone: Tone = 'ok') => {
    const id = Date.now() + Math.random();
    setList((l) => [...l, { id, text, tone }]);
    setTimeout(() => setList((l) => l.filter((t) => t.id !== id)), 4000);
  }, []);
  const value = useMemo(() => push, [push]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 top-16 z-50 mx-auto flex max-w-[560px] flex-col gap-2 px-4">
        {list.map((t) => (
          <div key={t.id} role="status" className={`rounded-md border px-4 py-3 text-sm font-medium ${
            t.tone === 'ok' ? 'border-cyan bg-raised text-ink' : t.tone === 'warn' ? 'border-warn bg-raised text-ink' : 'border-danger bg-raised text-ink'}`}>
            {t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);
