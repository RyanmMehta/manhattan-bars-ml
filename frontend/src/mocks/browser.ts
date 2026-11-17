// SYNTHETIC: starts the MSW mock API in the browser (VITE_API_MODE=mock or ?mock=1).
import { setupWorker } from 'msw/browser';
import { makeHandlers } from './handlers';

export async function startMockApi(base: string) {
  const worker = setupWorker(...makeHandlers(undefined, base.startsWith('http') ? `${base.replace(/\/$/, '')}` : base));
  await worker.start({ onUnhandledRequest: 'bypass', quiet: true, serviceWorker: { url: '/mockServiceWorker.js' } });
}
