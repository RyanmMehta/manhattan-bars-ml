import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { ApiError } from './api/client';
import type { Health } from './api/types';
import { AppShell } from './components/layout/AppShell';
import { ToastProvider } from './components/ui/Toast';
import type { ApiMode } from './config/env';
import { STALE_TIME_MS } from './config/thresholds';
import { AppRoutes } from './routes';
import { DataModeProvider } from './state/dataMode';
import { DemoClockProvider } from './state/demoClock';
import { PersonaProvider } from './state/persona';
import { PrefsProvider } from './state/prefs';

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: STALE_TIME_MS,
        retry: (n, e) => !(e instanceof ApiError && e.status >= 400 && e.status < 500) && n < 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export function Providers({
  children,
  mode,
  health,
  client,
}: {
  children: ReactNode;
  mode: ApiMode;
  health: Health | null;
  client?: QueryClient;
}) {
  const [qc] = useState(() => client ?? makeQueryClient());
  return (
    <QueryClientProvider client={qc}>
      <DataModeProvider mode={mode} health={health}>
        <DemoClockProvider healthNow={health?.demo_now ?? null}>
          <PrefsProvider>
            <PersonaProvider>
              <ToastProvider>{children}</ToastProvider>
            </PersonaProvider>
          </PrefsProvider>
        </DemoClockProvider>
      </DataModeProvider>
    </QueryClientProvider>
  );
}

export function App({ mode, health, notice }: { mode: ApiMode; health: Health | null; notice?: ReactNode }) {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Providers mode={mode} health={health}>
        <AppShell notice={notice}>
          <AppRoutes />
        </AppShell>
      </Providers>
    </BrowserRouter>
  );
}
