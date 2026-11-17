// T15: export mockup PNGs of every screen from the running app in mock mode (PRD §6).
// Usage: npm run mockups   (builds with --mode e2e, serves dist on :4174, screenshots with Chromium)
import { spawn, execSync } from 'node:child_process';
import { mkdirSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const outDir = join(root, 'mockups');
mkdirSync(outDir, { recursive: true });

let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  ({ chromium } = require('@playwright/test'));
}

const NOW = '2026-11-14T23:30:00-05:00';
const PORT = 4174;
const BASE = `http://localhost:${PORT}`;
// SYNTHETIC: demo preferences used for the mockups (hip-hop + r&b group of 4, OUTLINE §7 step 2).
const PREFS = {
  genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, max_cover_usd: 20, max_line_minutes: 15,
  max_distance_km: 1.5, lat: 40.7203, lon: -73.9881, group_size: 4,
};
const OWNER = '0370-23-127248';
const LOWCONF = '0370-23-131873';

const shots = [
  { file: '01-onboarding.png', path: '/onboarding', fresh: true },
  { file: '02-pick.png', path: '/tonight', act: async (p) => { await p.getByRole('button', { name: /Show 3 excluded/ }).click(); } , full: true },
  { file: '03-browse.png', path: '/browse' },
  { file: '04-venue.png', path: '/venue/0370-21-116653', full: true },
  { file: '05-map.png', path: '/map', wait: 'map' },
  { file: '06-heatmap.png', path: '/map', wait: 'map', act: async (p) => { await p.getByRole('switch', { name: /Heat/ }).click(); await p.waitForTimeout(800); } },
  { file: '07-vibe-check.png', path: `/scout?venue=${LOWCONF}`, act: async (p) => {
      await p.getByRole('button', { name: 'Crowd 3: Buzzing' }).click();
      await p.getByRole('button', { name: 'Some', exact: true }).click();
      await p.getByRole('button', { name: '5', exact: true }).click();
    } },
  { file: '08-leaderboard.png', path: '/scout/leaderboard' },
  { file: '09-bounties.png', path: '/scout/bounties' },
  { file: '10-run-my-night.png', path: '/plan', full: true },
  { file: '11-owner.png', path: `/owner/${OWNER}`, owner: true, full: true },
  { file: '11-owner-desktop.png', path: `/owner/${OWNER}`, owner: true, desktop: true },
  { file: '05-map-desktop.png', path: '/map', wait: 'map', desktop: true, act: async (p) => { await p.getByRole('switch', { name: /Heat/ }).click(); await p.waitForTimeout(800); } },
];

async function waitForServer(url, ms = 30000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { if ((await fetch(url)).ok) return; } catch { /* not up */ }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error('preview server did not start');
}

if (!process.argv.includes('--no-build')) execSync('npx vite build --mode e2e', { cwd: root, stdio: 'inherit' });
const server = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], { cwd: root, stdio: 'ignore' });
try {
  await waitForServer(BASE);
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const s of shots) {
    const ctx = await browser.newContext(
      s.desktop ? { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 } : { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 },
    );
    await ctx.addInitScript(({ prefs, fresh, owner }) => {
      if (!fresh) localStorage.setItem('na.prefs.v1', JSON.stringify(prefs));
      localStorage.setItem('na.persona.v1', JSON.stringify({ persona: owner ? 'owner' : 'planner', ownerVenueId: '0370-23-127248' }));
    }, { prefs: PREFS, fresh: !!s.fresh, owner: !!s.owner });
    const page = await ctx.newPage();
    const sep = s.path.includes('?') ? '&' : '?';
    await page.goto(`${BASE}${s.path}${sep}now=${encodeURIComponent(NOW)}`);
    await page.waitForSelector('main h1', { timeout: 15000 });
    await page.waitForFunction(() => !document.querySelector('[role="status"][aria-label="Loading"]'), null, { timeout: 15000 });
    if (s.wait === 'map') {
      await page.waitForFunction(() => document.querySelector('[data-testid="svg-map"]') || document.querySelector('[data-testid="maplibre-map"][data-ready="1"]'), null, { timeout: 20000 });
      await page.waitForTimeout(2500); // tiles
    }
    if (s.act) await s.act(page);
    if (s.full && !s.desktop) {
      // Full-page capture: pin header to the top and the tab bar to the page bottom.
      await page.addStyleTag({ content: "#root > div{position:relative} header{position:relative!important} nav[aria-label='Main']{position:absolute!important}" });
    }
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    const file = join(outDir, s.file);
    await page.screenshot({ path: file, fullPage: !!s.full && !s.desktop });
    const kb = Math.round(statSync(file).size / 1024);
    console.log(`${s.file}  ${kb} KB`);
    await ctx.close();
  }

  // Contact sheet: every mobile PNG as a thumbnail grid.
  const mobile = shots.filter((s) => !s.desktop).map((s) => s.file);
  const desk = shots.filter((s) => s.desktop).map((s) => s.file);
  const html = `<!doctype html><html><body style="margin:0;background:#0B0B12;color:#F3F3F7;font:14px Inter,system-ui,sans-serif;padding:32px">
    <h1 style="font:600 28px 'Space Grotesk',Inter,sans-serif;margin:0 0 4px">Nightlife Autopilot: frontend mockups</h1>
    <p style="margin:0 0 24px;color:#A3A3B8">Exported from the running app in mock mode at ${NOW} · all data synthetic (demo data)</p>
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:20px">${mobile.map((f) => `<figure style="margin:0"><div style="height:520px;overflow:hidden;border:1px solid #2A2A3A;border-radius:16px"><img src="file://${join(outDir, f)}" style="width:100%"></div><figcaption style="margin-top:6px;color:#A3A3B8">${f}</figcaption></figure>`).join('')}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:24px">${desk.map((f) => `<figure style="margin:0"><img src="file://${join(outDir, f)}" style="width:100%;border:1px solid #2A2A3A;border-radius:12px"><figcaption style="margin-top:6px;color:#A3A3B8">${f}</figcaption></figure>`).join('')}</div>
  </body></html>`;
  const sheetHtml = join(outDir, '.contact-sheet.html');
  writeFileSync(sheetHtml, html);
  const ctx = await browser.newContext({ viewport: { width: 1800, height: 1000 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto(`file://${sheetHtml}`);
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(outDir, 'contact-sheet.png'), fullPage: true });
  console.log('contact-sheet.png');
  unlinkSync(sheetHtml);
  await browser.close();
} finally {
  server.kill();
}
