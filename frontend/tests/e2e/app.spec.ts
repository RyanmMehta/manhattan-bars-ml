// E2E (RULES §5), mock mode, 390×844.
import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const NOW = '2026-11-14T23:30:00-05:00';
const PREFS = { genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, max_cover_usd: 20, max_line_minutes: 15, max_distance_km: 1.5, lat: 40.7203, lon: -73.9881, group_size: 4 };
const q = `now=${encodeURIComponent(NOW)}`;

async function withPrefs(page: Page) {
  await page.addInitScript((p) => localStorage.setItem('na.prefs.v1', JSON.stringify(p)), PREFS);
}
const errors: string[] = [];
test.beforeEach(({ page }) => {
  errors.length = 0;
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && !/tiles|Failed to load resource|maplibre|WebGL/i.test(m.text()) && errors.push(m.text()));
});
test.afterEach(() => expect(errors, 'no console errors').toEqual([]));

test('onboarding → pick → profile → directions (US-01, US-02, US-04)', async ({ page }) => {
  await page.goto(`/?${q}`);
  await expect(page).toHaveURL(/onboarding/);
  await page.getByRole('button', { name: 'Hip-hop' }).click();
  await page.getByRole('button', { name: 'R&B' }).click();
  await page.getByRole('switch', { name: /dance/ }).click();
  await page.getByRole('button', { name: /Save/ }).click();
  const hero = page.getByTestId('pick-hero');
  await expect(hero).toContainText('Subject');
  await expect(hero).toContainText('cover not reported tonight');
  await page.getByRole('button', { name: 'Show 3 excluded' }).click();
  await expect(page.getByTestId('excluded-card')).toHaveCount(3);
  await hero.getByRole('link', { name: 'Open venue' }).click();
  await expect(page.getByRole('heading', { name: 'Subject' })).toBeVisible();
  await expect(page.getByTestId('directions')).toHaveAttribute('href', /maps/);
});

test('browse + filter + search (US-03)', async ({ page }) => {
  await withPrefs(page);
  await page.goto(`/browse?${q}`);
  await expect(page.getByTestId('venue-card')).toHaveCount(35);
  await page.getByLabel('Search venues').fill('mehanata');
  await expect(page.getByTestId('venue-card')).toHaveCount(1);
  await page.getByLabel('Search venues').fill('');
  await page.getByLabel('Genre').selectOption('hip-hop');
  // Search debounce (250 ms) can briefly combine the old query with the new genre; wait for the settled list.
  await expect.poll(async () => { const n = await page.getByTestId('venue-card').count(); return n > 0 && n < 35; }).toBe(true);
});

test('vibe check submit in < 10 s of scripted steps (US-06)', async ({ page }) => {
  await withPrefs(page);
  await page.goto(`/scout/bounties?${q}`);
  await page.getByTestId('bounty').first().click();
  const t0 = Date.now();
  await page.getByRole('button', { name: 'Crowd 3: Buzzing' }).click();
  await page.getByRole('button', { name: 'Some', exact: true }).click();
  await page.getByRole('button', { name: '5', exact: true }).click();
  await page.getByRole('button', { name: 'Send vibe check' }).click();
  await expect(page.getByText(/\+60 pts pending/)).toBeVisible();
  expect(Date.now() - t0).toBeLessThan(10_000);
  await expect(page.getByRole('heading', { name: 'Clockwork Bar' })).toBeVisible();
  // leaderboard: demo scout moved up
  await page.getByRole('link', { name: /Scout/ }).click();
  await page.getByRole('link', { name: /Leaderboard/ }).click();
  await expect(page.getByTestId('me-row')).toContainText('80');
});

test('owner update (US-09)', async ({ page }) => {
  await page.goto(`/owner/0370-23-127248?${q}`);
  await expect(page.getByTestId('kpis')).toBeVisible();
  await page.getByLabel('Offer', { exact: true }).fill('$10 cover before midnight');
  await page.getByLabel('DJ').fill('Balkan Beat');
  await expect(page.getByTestId('offer-card')).toContainText('DJ Balkan Beat');
  await page.getByRole('button', { name: 'Post update' }).click();
  await expect(page.getByText(/Update posted/)).toBeVisible();
  await page.goto(`/venue/0370-23-127248?${q}`);
  await expect(page.getByTestId('offer-card')).toHaveCount(0); // new page = fresh mock db
});

test('demo time travel changes the map and pick (US-10, US-05)', async ({ page }) => {
  await withPrefs(page);
  await page.goto(`/tonight?demo=1&${q}`);
  await expect(page.getByTestId('demo-panel')).toBeVisible();
  await expect(page.getByTestId('demo-banner')).toContainText('11:30 PM');
  const req = page.waitForRequest((r) => r.url().includes('/api/recommend') && r.url().includes('22%3A30'));
  await page.getByRole('button', { name: '−1 h' }).click();
  await req;
  await expect(page.getByTestId('demo-banner')).toContainText('10:30 PM');
  await expect(page.getByTestId('pick-hero')).toContainText('78');
});

const ROUTES = ['/onboarding', '/tonight', '/browse', '/map?map=svg', '/venue/0370-21-116653', '/scout', '/scout/leaderboard', '/scout/bounties', '/plan', '/owner/0370-23-127248', '/more'];
for (const r of ROUTES) {
  test(`synthetic badge + a11y on ${r} (US-11)`, async ({ page }) => {
    await withPrefs(page);
    await page.goto(`${r}${r.includes('?') ? '&' : '?'}${q}`);
    await expect(page.locator('main h1')).toBeVisible();
    await expect(page.getByTestId('demo-banner')).toBeVisible();
    await page.waitForFunction(() => !document.querySelector('[aria-label="Loading"]'));
    await page.addScriptTag({ content: axeSource });
    const res = await page.evaluate(async () => {
      // @ts-expect-error injected
      const r = await window.axe.run(document, { resultTypes: ['violations'] });
      return (r.violations as { id: string; impact: string; nodes: unknown[] }[]).filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => `${v.id} (${v.nodes.length})`);
    });
    expect(res).toEqual([]);
  });
}
