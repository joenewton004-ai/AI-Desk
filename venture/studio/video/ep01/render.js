// Render HTML slides to PNG with Playwright (Chromium).
// Usage: node render.js jobs.json
// jobs.json = [{"html": "/abs/a.html", "png": "/abs/a.png", "w": 1920, "h": 1080, "scale": 2}, ...]
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch();
  const groups = {};
  for (const j of jobs) {
    const key = `${j.w}x${j.h}@${j.scale || 1}`;
    (groups[key] = groups[key] || []).push(j);
  }
  for (const key of Object.keys(groups)) {
    const g = groups[key];
    const ctx = await browser.newContext({
      viewport: { width: g[0].w, height: g[0].h },
      deviceScaleFactor: g[0].scale || 1,
    });
    const page = await ctx.newPage();
    for (const j of g) {
      await page.goto('file://' + j.html);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: j.png, fullPage: !!j.full });
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`rendered ${jobs.length} png`);
})();
