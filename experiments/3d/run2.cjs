const { chromium } = require("../../web/node_modules/playwright");
const url = "file://" + __dirname + "/bench2.html";
(async () => {
  const b = await chromium.launch({ headless: false });
  const p = await b.newPage({ viewport: { width: 800, height: 800 } });
  await p.goto("chrome://gpu"); await p.waitForTimeout(1500);
  const gpu = await p.evaluate(() => { const t = document.querySelector("info-view")?.shadowRoot?.textContent || document.body.innerText; const m = t.match(/Rasterization:\s*([^\n]+)/); return m ? m[1].trim() : t.slice(0, 300); });
  console.log("chrome://gpu Rasterization:", gpu);
  for (const n of [40, 60, 80, 100]) {
    await p.goto(`${url}?n=${n}&kind=torus&frames=120`);
    await p.waitForFunction(() => window.done, null, { timeout: 120000 });
    const r = await p.evaluate(() => {
      const med = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
      const ps = parts.slice(10);
      return { frame: med(frameTimes.slice(10)), math: med(ps.map((x) => x[0])), str: med(ps.map((x) => x[1])), dom: med(ps.map((x) => x[2])) };
    });
    const rest = r.frame - r.math - r.str - r.dom;
    console.log(`faces=${n * n}: frame ${r.frame.toFixed(1)} ms | arithmetic ${r.math.toFixed(1)} | strings and colors ${r.str.toFixed(1)} | writing to the page ${r.dom.toFixed(1)} | browser drawing and idle ${rest.toFixed(1)}`);
  }
  await b.close();
})();
