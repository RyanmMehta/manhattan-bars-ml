// Browser smoke test for the class demo path (integration-owned), against the LIVE API.
// Node Playwright with the preinstalled Chromium; viewport 390x844 (PRD N3).
// Usage: BASE_URL=http://127.0.0.1:4173 API_URL=http://127.0.0.1:8765 OUT_DIR=/tmp/x node tests/e2e/smoke.cjs
// Selectors follow frontend's own e2e spec (frontend/tests/e2e) so both suites break together.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:4173').replace(/\/$/, '');
const API = (process.env.API_URL || '').replace(/\/$/, '');
const OUT = process.env.OUT_DIR || '.';
const NOW = process.env.DEMO_NOW || '2026-11-14T23:30:00-05:00';
const Q = `now=${encodeURIComponent(NOW)}`;
const steps = [];
const consoleErrors = [];
const ctxData = {};

async function step(page, name, fn) {
  try {
    await fn();
    steps.push({ name, ok: true });
  } catch (e) {
    steps.push({ name, ok: false, error: String((e && e.message) || e).split('\n')[0].slice(0, 400) });
  }
  await page.screenshot({ path: path.join(OUT, `${String(steps.length).padStart(2, '0')}-${name.replace(/\W+/g, '_')}.png`) }).catch(() => {});
}

async function api(p) {
  const r = await fetch(`${API}${p}`);
  if (!r.ok) throw new Error(`${p} -> ${r.status}`);
  return r.json();
}

const must = async (loc, timeout = 10000) => loc.first().waitFor({ state: 'visible', timeout });
const banner = (page) => page.getByTestId('demo-banner');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => consoleErrors.push(String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error' && !/tiles|maplibre|WebGL|favicon/i.test(m.text())) consoleErrors.push(m.text());
  });

  await step(page, 'health is real recs at demo time', async () => {
    if (!API) return;
    const h = await api('/api/health');
    if (!h.ok || h.recs !== 'real' || !String(h.demo_now).startsWith('2026-11-14T23:30')) throw new Error(JSON.stringify(h));
  });

  await step(page, 'onboarding', async () => {
    await page.goto(`${BASE}/?${Q}`, { waitUntil: 'networkidle' });
    await page.waitForURL(/onboarding/, { timeout: 10000 });
    await page.getByRole('button', { name: 'Hip-hop' }).click();
    await page.getByRole('button', { name: 'R&B' }).click();
    await page.getByRole('switch', { name: /dance/i }).click();
    const crowd = page.getByLabel('Crowd', { exact: true });
    await crowd.fill('4');
    if ((await crowd.inputValue()) !== '4') throw new Error('could not set crowd to 4');
    page.on('request', (r) => {
      if (r.url().includes('/api/recommend') && !ctxData.recommendBody) ctxData.recommendBody = r.postData();
    });
    await page.getByRole('button', { name: /Save/ }).click();
    await page.waitForURL(/tonight/, { timeout: 10000 });
  });

  await step(page, 'tonight pick with scores and reasons', async () => {
    const hero = page.getByTestId('pick-hero');
    await must(hero, 15000);
    const txt = await hero.innerText();
    if (!/match/i.test(txt)) throw new Error(`no match score in hero: ${txt.slice(0, 200)}`);
    ctxData.heroText = txt.slice(0, 300);
    const m = txt.match(/VIBE\s+(\d+)/i);
    if (!m) throw new Error(`no vibe number in hero: ${txt.slice(0, 200)}`);
    if (Number(m[1]) < 35) throw new Error(`#1 pick has vibe ${m[1]} (< 35, "Chill") for hip-hop/r&b + dancing + crowd 4`);
  });

  await step(page, 'demo badge + clock 11:30 PM on tonight', async () => {
    await must(banner(page));
    const t = await banner(page).first().innerText();
    if (!/demo data/i.test(t) || !/11:30\s*PM/i.test(t)) throw new Error(`banner: ${t}`);
  });

  await step(page, 'vibe band label (Chill/Lively/Packed/No fresh reports)', async () => {
    await must(page.getByText(/\b(Chill|Lively|Packed|No fresh reports)\b/), 8000);
  });

  await step(page, 'complaint risk never labelled quality', async () => {
    const body = await page.locator('body').innerText();
    if (/quality/i.test(body)) throw new Error('found "quality" wording on screen');
  });

  await step(page, 'venue profile', async () => {
    await page.getByTestId('pick-hero').getByRole('link', { name: /Open venue/i }).click();
    await page.waitForURL(/\/venue\//, { timeout: 10000 });
    ctxData.venueId = decodeURIComponent(page.url().split('/venue/')[1].split(/[?#]/)[0]);
    await must(page.locator('main h1'));
    await must(banner(page));
  });

  await step(page, 'browse lists 35 venues', async () => {
    await page.goto(`${BASE}/browse?${Q}`, { waitUntil: 'networkidle' });
    await must(page.getByTestId('venue-card'), 15000);
    const n = await page.getByTestId('venue-card').count();
    if (n !== 35) throw new Error(`venue cards: ${n}`);
  });

  await step(page, 'scout vibe check updates live state', async () => {
    const vid = ctxData.venueId;
    const before = API ? await api(`/api/venues/${encodeURIComponent(vid)}/state`) : null;
    await page.goto(`${BASE}/scout?venue=${encodeURIComponent(vid)}&${Q}`, { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: /^Crowd 5/ }).click();
    await page.getByRole('button', { name: 'Lots', exact: true }).click();
    await page.getByRole('button', { name: '5', exact: true }).click();
    await page.getByRole('button', { name: 'Send vibe check' }).click();
    await must(page.getByText(/pts pending/), 10000);
    await page.waitForURL(/\/venue\//, { timeout: 10000 });
    if (API) {
      const after = await api(`/api/venues/${encodeURIComponent(vid)}/state`);
      if (after.n_reports !== before.n_reports + 1) throw new Error(`n_reports ${before.n_reports} -> ${after.n_reports}`);
      if (!(after.freshness_minutes <= 1)) throw new Error(`freshness ${after.freshness_minutes}`);
    }
  });

  await step(page, 'leaderboard', async () => {
    await page.goto(`${BASE}/scout/leaderboard?${Q}`, { waitUntil: 'networkidle' });
    await must(page.locator('[data-testid="lb-row"], [data-testid="me-row"]'), 10000);
    await must(banner(page));
  });

  await step(page, 'bounties', async () => {
    await page.goto(`${BASE}/scout/bounties?${Q}`, { waitUntil: 'networkidle' });
    await must(page.locator('main h1'));
    await must(banner(page));
  });

  await step(page, 'owner posts update, profile shows offer', async () => {
    const all = API ? await api(`/api/venues?launch_only=true&${Q}`) : [];
    const owned = (all.find((v) => v.venue_id !== ctxData.venueId) || {}).venue_id || '0370-23-127248';
    ctxData.ownerVenue = owned;
    await page.goto(`${BASE}/owner/${encodeURIComponent(owned)}?${Q}`, { waitUntil: 'networkidle' });
    await must(page.getByTestId('kpis'), 15000);
    await page.getByLabel('Offer', { exact: true }).fill('$10 cover before midnight');
    await page.getByRole('button', { name: 'Post update' }).click();
    await must(page.getByText(/Update posted/), 10000);
    await page.goto(`${BASE}/venue/${encodeURIComponent(owned)}?${Q}`, { waitUntil: 'networkidle' });
    await must(page.getByTestId('offer-card'), 10000);
    const t = await page.getByTestId('offer-card').first().innerText();
    if (!/\$10 cover before midnight/.test(t)) throw new Error(`offer card: ${t}`);
  });

  await step(page, 'run my night (if enabled)', async () => {
    await page.goto(`${BASE}/plan?${Q}`, { waitUntil: 'networkidle' });
    await must(page.locator('main h1'));
    await must(banner(page));
  });

  await step(page, 'map renders without paid tile keys', async () => {
    await page.goto(`${BASE}/map?map=svg&${Q}`, { waitUntil: 'networkidle' });
    await must(page.locator('main h1'));
    const html = await page.content();
    if (/api\.mapbox\.com|access_token=|maps\.googleapis\.com/.test(html)) throw new Error('paid map tiles referenced');
  });

  await step(page, 'no console errors', async () => {
    if (consoleErrors.length) throw new Error(consoleErrors.slice(0, 5).join(' | '));
  });

  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ base: BASE, api: API, steps, consoleErrors, ctxData }, null, 1));
  for (const s of steps) console.log(`${s.ok ? 'PASS' : 'FAIL'} ${s.name}${s.ok ? '' : ' — ' + s.error}`);
  await browser.close();
  process.exit(steps.every((s) => s.ok) ? 0 : 1);
})();
