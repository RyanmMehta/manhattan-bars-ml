// Browser smoke test for the demo path (integration-owned). Node Playwright, preinstalled Chromium.
// Usage: BASE_URL=http://127.0.0.1:4173 OUT_DIR=/tmp/x node tests/e2e/smoke.cjs
// Steps are written against visible text so they survive markup changes; selectors are
// refined in tests/e2e/README after the frontend merge.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:4173').replace(/\/$/, '');
const OUT = process.env.OUT_DIR || '.';
const DEMO_NOW = process.env.DEMO_NOW || '2026-11-14T23:30:00-05:00';
const steps = [];
const consoleErrors = [];

async function step(name, fn, page) {
  try {
    await fn();
    steps.push({ name, ok: true });
  } catch (e) {
    steps.push({ name, ok: false, error: String(e && e.message || e).slice(0, 500) });
  }
  if (page) await page.screenshot({ path: path.join(OUT, `${steps.length}-${name.replace(/\W+/g, '_')}.png`) }).catch(() => {});
}

const badge = (page) => page.getByText(/demo data/i).first();

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => consoleErrors.push(String(e)));

  await step('load app', async () => {
    const r = await page.goto(`${BASE}/?now=${encodeURIComponent(DEMO_NOW)}`, { waitUntil: 'networkidle' });
    if (!r || !r.ok()) throw new Error(`HTTP ${r && r.status()}`);
  }, page);

  // Onboarding (if shown): accept defaults / continue until the Tonight list appears.
  await step('onboarding -> tonight', async () => {
    for (let i = 0; i < 6; i++) {
      if (await page.getByText(/tonight/i).first().isVisible().catch(() => false) &&
          await page.getByText(/match/i).first().isVisible().catch(() => false)) return;
      const btn = page.getByRole('button', { name: /(get started|continue|next|show|find|let'?s go|done|skip)/i }).first();
      if (await btn.isVisible().catch(() => false)) { await btn.click(); await page.waitForTimeout(600); } else break;
    }
    await page.getByText(/match/i).first().waitFor({ timeout: 15000 });
  }, page);

  await step('demo badge on tonight', async () => { await badge(page).waitFor({ timeout: 5000 }); }, page);

  await step('clock chip shows demo time', async () => {
    await page.getByText(/11:30\s*(PM|pm)?/).first().waitFor({ timeout: 5000 });
  }, page);

  await step('vibe band label present', async () => {
    await page.getByText(/\b(Chill|Lively|Packed|No fresh reports)\b/).first().waitFor({ timeout: 5000 });
  }, page);

  await step('complaint risk never labelled quality', async () => {
    const body = await page.locator('body').innerText();
    if (/quality/i.test(body)) throw new Error('found "quality" wording on screen');
  }, page);

  await step('open venue profile', async () => {
    const card = page.locator('a[href*="/venue"], [data-testid*="venue-card"], article').first();
    await card.click();
    await page.waitForTimeout(800);
    await badge(page).waitFor({ timeout: 5000 });
  }, page);

  await step('vibe check submit', async () => {
    const open = page.getByRole('button', { name: /(vibe check|report|be the scout)/i }).first();
    await open.click();
    await page.waitForTimeout(500);
    const submit = page.getByRole('button', { name: /(submit|send|post)/i }).first();
    await submit.click();
    await page.getByText(/(thanks|submitted|points|pending)/i).first().waitFor({ timeout: 10000 });
  }, page);

  await step('leaderboard', async () => {
    await page.goto(`${BASE}/leaderboard?now=${encodeURIComponent(DEMO_NOW)}`, { waitUntil: 'networkidle' });
    await page.getByText(/(leaderboard|top scouts)/i).first().waitFor({ timeout: 8000 });
    await badge(page).waitFor({ timeout: 5000 });
  }, page);

  await step('no paid map keys in bundle', async () => {
    const html = await page.content();
    if (/api\.mapbox\.com|access_token=|maps\.googleapis\.com/.test(html)) throw new Error('paid map tiles referenced');
  }, page);

  await step('no console errors', async () => {
    const real = consoleErrors.filter((e) => !/favicon|ResizeObserver/i.test(e));
    if (real.length) throw new Error(real.slice(0, 5).join(' | '));
  });

  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ base: BASE, steps, consoleErrors }, null, 1));
  for (const s of steps) console.log(`${s.ok ? 'PASS' : 'FAIL'} ${s.name}${s.ok ? '' : ' — ' + s.error}`);
  await browser.close();
  process.exit(steps.every((s) => s.ok) ? 0 : 1);
})();
