import { defineConfig, devices } from '@playwright/test';

// Live-mode e2e (T16): needs the backend on http://localhost:8000. `npm run e2e:live`.
export default defineConfig({
  testDir: 'tests/e2e-live',
  timeout: 45_000,
  workers: 2,
  reporter: 'list',
  use: { baseURL: 'http://localhost:4175', viewport: { width: 390, height: 844 }, trace: 'off' },
  projects: [{ name: 'live-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } } }],
  webServer: {
    command: 'npx vite build --mode live --outDir dist-live && npx vite preview --outDir dist-live --port 4175 --strictPort',
    port: 4175,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
