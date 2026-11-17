// Live-mode e2e against the real backend (recs + live_sim.db). Asserts structure, not fixture names.
import { test, expect, type Page } from '@playwright/test';

const NOW = '2026-11-14T23:30:00-05:00';
const q = `now=${encodeURIComponent(NOW)}`;
const PREFS = { genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, max_cover_usd: 20, max_line_minutes: 15, max_distance_km: 1.5, lat: 40.7203, lon: -73.9881, group_size: 4 };
const errors: string[] = [];

test.beforeAll(async ({ request }) => {
  const h = await request.get('http://localhost:8000/api/health').catch(() => null);
  test.skip(!h || !h.ok(), 'backend not running on :8000');
});
test.beforeEach(async ({ page }) => {
  errors.length = 0;
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && !/tiles|Failed to load resource|maplibre|WebGL/i.test(m.text()) && errors.push(m.text()));
  page.on('request', (r) => {
    if (r.url().includes('mockServiceWorker')) errors.push('mock worker loaded in live mode');
  });
  await page.addInitScript((p) => localStorage.setItem('na.prefs.v1', JSON.stringify(p)), PREFS);
});
test.afterEach(() => expect(errors).toEqual([]));

async function apiCall(page: Page, path: string) {
  return page.waitForResponse((r) => r.url().includes(path) && r.request().method() !== 'OPTIONS');
}

test('pick comes from the live /api/recommend (US-02)', async ({ page }) => {
  const resp = apiCall(page, '/api/recommend');
  await page.goto(`/tonight?${q}`);
  const r = await resp;
  expect(r.status()).toBe(200);
  expect(r.url()).toContain('now=');
  await expect(page.getByTestId('pick-hero')).toBeVisible();
  await expect(page.getByTestId('demo-banner')).toContainText('Demo data'); // health.data = synthetic
  await expect(page.getByText('offline mock API')).toHaveCount(0);
});

test('browse lists 35 launch venues with distance (US-03)', async ({ page }) => {
  await page.goto(`/browse?${q}`);
  await expect(page.getByTestId('venue-card')).toHaveCount(35);
  await expect(page.getByTestId('venue-count')).toHaveText('35 venues');
});

test('venue profile shows complaint_risk label + level (US-04, CR-19)', async ({ page }) => {
  await page.goto(`/browse?${q}`);
  await page.getByTestId('venue-card').first().getByRole('link').first().click();
  await expect(page.getByTestId('complaint-risk')).toContainText('311 noise-complaint risk');
  await expect(page.getByTestId('complaint-risk')).toContainText(/Low|Medium|High|not reported/);
});

test('vibe check posts to the backend and pays points (US-06)', async ({ page }) => {
  await page.goto(`/scout/bounties?${q}`);
  const bounty = page.getByTestId('bounty').first();
  if (await bounty.count()) await bounty.click();
  else await page.goto(`/scout?venue=0370-23-131873&${q}`);
  await page.getByRole('button', { name: 'Crowd 3: Buzzing' }).click();
  await page.getByRole('button', { name: 'Some', exact: true }).click();
  await page.getByRole('button', { name: '5', exact: true }).click();
  const resp = apiCall(page, '/api/reports');
  await page.getByRole('button', { name: 'Send vibe check' }).click();
  expect((await resp).status()).toBe(201);
  await expect(page.getByText(/pts pending/)).toBeVisible();
});

test('owner dashboard loads with owner token and posts an update (US-09)', async ({ page }) => {
  await page.goto(`/owner/0370-23-127248?${q}`);
  await expect(page.getByTestId('kpis')).toBeVisible();
  await page.getByLabel('Offer', { exact: true }).fill('$10 cover before midnight');
  await page.getByLabel('DJ').fill('Balkan Beat');
  const resp = apiCall(page, '/api/owner/0370-23-127248/updates');
  await page.getByRole('button', { name: 'Post update' }).click();
  expect((await resp).status()).toBe(201);
  await expect(page.getByText(/Update posted/)).toBeVisible();
  await page.goto(`/venue/0370-23-127248?${q}`);
  await expect(page.getByTestId('offer-card').first()).toContainText('$10 cover before midnight');
});

test('leaderboard, bounties, plan, map, feedback render live data (US-05/07/08)', async ({ page }) => {
  await page.goto(`/scout/leaderboard?${q}`);
  await expect(page.getByTestId('lb-row').first()).toBeVisible();
  await page.goto(`/plan?${q}`);
  await expect(page.getByTestId('plan-stop').first()).toBeVisible();
  await expect(page.getByTestId('plan-stop').first()).not.toContainText(/\d+\.\d+ min walk/);
  await page.goto(`/map?map=svg&${q}`);
  await expect(page.getByTestId('svg-map')).toBeVisible();
  await page.goto(`/venue/0370-21-116653?${q}`);
  const fb = apiCall(page, '/api/feedback');
  await page.getByRole('button', { name: 'Rate 4 of 5' }).click();
  expect((await fb).status()).toBe(201);
  await expect(page.getByText(/Thanks/)).toBeVisible();
});
