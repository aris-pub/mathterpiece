const { chromium } = require("../../web/node_modules/playwright");
const url = "file://" + __dirname + "/bench.html";
(async () => {
  const b = await chromium.launch({ headless: process.argv[2] !== "headed" });
  const p = await b.newPage({ viewport: { width: 800, height: 800 } });
  for (const kind of ["graph", "torus"]) for (const n of [20, 40, 60, 80, 100]) {
    await p.goto(`${url}?n=${n}&kind=${kind}&frames=120`);
    await p.waitForFunction(() => window.done, null, { timeout: 120000 });
    const r = await p.evaluate(() => {
      const med = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
      return { frame: med(frameTimes.slice(10)), js: med(jsTimes.slice(10)) };
    });
    console.log(`${kind} faces=${n * n} median frame ${r.frame.toFixed(1)} ms (${(1000 / r.frame).toFixed(0)} fps), of which mtp-side compute ${r.js.toFixed(1)} ms`);
  }
  for (const [kind, n, seam] of [["torus", 40, "stroke"], ["torus", 40, "none"], ["graph", 40, "stroke"]]) {
    await p.goto(`${url}?n=${n}&kind=${kind}&seam=${seam}`);
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${__dirname}/${kind}-${n}-${seam}.png` });
  }
  await b.close();
})();
