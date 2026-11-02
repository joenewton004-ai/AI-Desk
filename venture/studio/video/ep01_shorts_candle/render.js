// Render avatar-Short stills with Playwright (Chromium): one page load, many states.
// Usage: node render.js job.json
// job.json = {"template": "/abs/frame.html", "report": "/abs/report.json",
//             "states": [{"png": "/abs/s000.png", "card": "<html>", "caption": "<html>", "avatar": "<svg>", "bounce": 0}]}
// Writes report.json = [{png, fs, lines, overflow}] (caption fit info, checked by build.py).
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto('file://' + job.template);
  await page.evaluate(() => document.fonts.ready);
  const report = [];
  for (const s of job.states) {
    const info = await page.evaluate((st) => window.setState(st), s);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: s.png });
    report.push(Object.assign({ png: s.png }, info));
  }
  await browser.close();
  fs.writeFileSync(job.report, JSON.stringify(report, null, 1));
  console.log(`rendered ${job.states.length} png`);
})();
