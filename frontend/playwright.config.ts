import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';

const exe = '/opt/pw-browsers/chromium';
// Use the preinstalled Chromium; only set executablePath if Playwright can't find its own build.
const launchOptions = process.env.PW_USE_SYSTEM && existsSync(exe) ? { executablePath: exe } : {};

export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 30_000,
  fullyParallel: true,
  workers: 3,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    viewport: { width: 390, height: 844 },
    trace: 'off',
    launchOptions,
  },
  projects: [{ name: 'mobile-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } } }],
  webServer: {
    command: 'npx vite build --mode e2e && npx vite preview --port 4173 --strictPort',
    port: 4173,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
