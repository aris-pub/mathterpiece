// Frame-time baseline: how long the runtime takes to answer one reader action, on every example
// with a slider, a drag or a play. Run from web/: node bench/frames.mjs (vite must be serving on
// port 5199: pnpm exec vite --port 5199). Phase 5 of the rebuild runs the same measurement.
import { chromium } from "playwright";

const BASE = "http://localhost:5199/";
const STEPS = 60;
const examples = process.argv.slice(2);

function stats(ms) {
  const s = [...ms].sort((a, b) => a - b);
  const mean = s.reduce((a, b) => a + b, 0) / s.length;
  return { mean: +mean.toFixed(2), p95: +s[Math.floor(s.length * 0.95)].toFixed(2), max: +s.at(-1).toFixed(2) };
}

// The runtime's own work for one input: its handlers, any animation-frame callbacks they queue,
// and the style and layout that follow. Painting is the browser's and is left out, as is waiting
// for the screen's next refresh, which would hide the runtime's cost under the frame rate.
const ACT = `async (act) => {
  window.__rafWork = 0;
  const t0 = performance.now();
  act();
  document.body.offsetHeight;
  const sync = performance.now() - t0;
  await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
  return sync + window.__rafWork;
}`;

// Times every animation-frame callback the page runs, so queued redraws and play frames count.
const TIME_RAF = () => {
  const raf = window.requestAnimationFrame.bind(window);
  window.__rafWork = 0;
  window.requestAnimationFrame = (cb) =>
    raf((t) => {
      const t0 = performance.now();
      cb(t);
      document.body.offsetHeight;
      window.__rafWork += performance.now() - t0;
    });
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
await page.addInitScript(TIME_RAF);
const results = {};
for (const name of examples) {
  await page.goto(`${BASE}?example=${name}`);
  await page.waitForSelector("mtp-canvas svg");
  await page.waitForTimeout(300);
  const out = {};
  // Slider: move the first slider's knob across its whole track.
  if (await page.locator("mtp-slider input").count()) {
    const times = [];
    for (let k = 0; k <= STEPS; k++) {
      times.push(
        await page.evaluate(
          `(${ACT})(() => { const i = document.querySelector("mtp-slider input"); i.value = String(${k} / ${STEPS}); i.dispatchEvent(new Event("input", { bubbles: true })); })`,
        ),
      );
    }
    out.slider = stats(times);
  }
  // Drag: press the first draggable shape and move the pointer in a circle around it, with the
  // pointer events dispatched in the page so each move's work is timed alone.
  if (await page.evaluate(() => [...document.querySelectorAll("mtp-canvas svg [data-mtp-id]")].some((e) => e.style.cursor === "grab"))) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll("mtp-canvas svg [data-mtp-id]")].find((e) => e.style.cursor === "grab");
      const b = el.getBoundingClientRect();
      window.__drag = { el, svg: el.ownerSVGElement, x: b.x + b.width / 2, y: b.y + b.height / 2 };
      const at = (x, y, type, target) =>
        target.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, isPrimary: true }));
      window.__dragTo = (k, n) => {
        const d = window.__drag;
        at(d.x + 40 * Math.cos((2 * Math.PI * k) / n), d.y + 40 * Math.sin((2 * Math.PI * k) / n), "pointermove", d.svg);
      };
      at(window.__drag.x, window.__drag.y, "pointerdown", el);
    });
    const times = [];
    for (let k = 1; k <= STEPS; k++) times.push(await page.evaluate(`(${ACT})(() => window.__dragTo(${k}, ${STEPS}))`));
    await page.evaluate(() => window.__drag.svg.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 })));
    out.drag = stats(times);
  }
  // Play: press play and record the runtime's work in each animation frame for two seconds.
  if (await page.locator("mtp-play button").count()) {
    await page.locator("mtp-play button").first().click();
    out.play = stats(
      await page.evaluate(
        () =>
          new Promise((done) => {
            const work = [];
            const end = performance.now() + 2000;
            const sample = () => {
              work.push(window.__rafWork);
              window.__rafWork = 0;
              if (performance.now() < end) setTimeout(sample, 16);
              else done(work.slice(1).filter((w) => w > 0));
            };
            window.__rafWork = 0;
            setTimeout(sample, 16);
          }),
      ),
    );
  }
  results[name] = out;
  console.log(name, JSON.stringify(out));
}
await browser.close();
