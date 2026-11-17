import { test, expect } from '@playwright/test';
// PRD N1: no horizontal scroll at 360–1440 px.
for (const w of [360, 390]) {
  for (const r of ['/tonight', '/venue/0370-21-116653', '/owner/0370-23-127248', '/scout']) {
    test(`no horizontal scroll at ${w}px on ${r}`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 800 });
      await page.goto(`${r}?now=2026-11-14T23%3A30%3A00-05%3A00`);
      await expect(page.locator('main h1')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(w);
    });
  }
}
