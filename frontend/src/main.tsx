import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { api, configureClient } from './api/client';
import type { Health } from './api/types';
import { apiMode, env } from './config/env';
import { HEALTH_TIMEOUT_MS } from './config/thresholds';
import './styles/index.css';

function switchToMock() {
  try {
    sessionStorage.setItem('na.mode.v1', 'mock');
  } catch {
    /* ignore */
  }
  window.location.reload();
}

async function boot() {
  const mode = apiMode();
  configureClient({ base: env.apiBase });
  let health: Health | null = null;
  let notice: JSX.Element | undefined;

  if (mode === 'mock') {
    // SYNTHETIC: mock API (MSW) instead of the backend. Real source: VITE_API_MODE=live.
    const { startMockApi } = await import('./mocks/browser');
    await startMockApi(env.apiBase);
    health = await api.health().catch(() => null);
  } else {
    // PRD R9: warm-up ping; if the backend is slow (> 5 s) offer mock mode.
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), HEALTH_TIMEOUT_MS);
    try {
      health = await api.health(ctl.signal);
    } catch {
      notice = (
        <div role="alert" className="border-b border-danger/50 bg-danger/10 px-4 py-2 text-center text-sm">
          The live API isn’t answering.{' '}
          <button type="button" className="min-h-[44px] underline" onClick={switchToMock}>
            Use demo mode
          </button>
        </div>
      );
    } finally {
      clearTimeout(t);
    }
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App mode={mode} health={health} notice={notice} />
    </StrictMode>,
  );
}

void boot();
