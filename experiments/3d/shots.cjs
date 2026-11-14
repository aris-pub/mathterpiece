const { chromium } = require("../../web/node_modules/playwright");
const url = "file://" + __dirname + "/sweep.html";
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 760, height: 760 }, deviceScaleFactor: 2 });
  const errs = []; p.on("pageerror", (e) => errs.push(String(e)));
  for (const t of [0, 3, 4.5, 6, 8]) {
    await p.goto(`${url}?t=${t}`); await p.waitForTimeout(200);
    await p.locator("svg").screenshot({ path: `${__dirname}/sweep-${t}.png` });
  }
  await p.goto(`${url}?t=3`); await p.waitForTimeout(200);
  await p.hover('.term[data-for="meridian"]');
  await p.screenshot({ path: `${__dirname}/sweep-hover.png` });
  console.log("errors:", errs);
  // A recording of one full sweep.
  const ctx = await b.newContext({ viewport: { width: 760, height: 700 }, recordVideo: { dir: __dirname + "/video", size: { width: 760, height: 700 } } });
  const v = await ctx.newPage(); await v.goto(url); await v.waitForTimeout(11000);
  const path = await v.video().path(); await ctx.close(); console.log("video:", path);
  await b.close();
})();
