// Speed on an imitated mid-range phone: builds each example (but house.mtp) with mtp build into
// perf/pages/ (git-ignored), opens it as a file in Chromium at 390 x 844, touch, 3 device pixels
// a pixel and the CPU slowed 4 times, and drives every slider, button, play, toggle, drag, shape
// click, pointer listener and formula term it finds. Fails when a page takes over 2 s to draw or
// an update over 16 ms of work. What an update's work is: the time in the event's handlers, plus
// the forced style and layout after them, plus every animation-frame callback in the next frame,
// with style and layout after each; for what starts an animation, its longest frame. Waiting for
// the screen's refresh and painting are left out, since two frames alone take 33 ms; the time to
// the next frame is shown, unjudged.
//
// Run from web/: node perf/phone.mjs [example ...]
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";
import { animationCost, failed, table } from "./report.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const EXAMPLES = join(ROOT, "examples");
const PAGES = join(HERE, "pages");
// Each example's driving stops starting new interactions after this long.
const EXAMPLE_MS = 40_000;
const SLIDER_STOPS = 8;
const DRAG_STEPS = 30;
const SWEEP_STEPS = 30;
// How many of each kind of shape interaction one example drives: some have dozens of shapes.
const MAX_SHAPES = 4;
const ANIMATION_MS = 1500;
const TOGGLE_MS = 600;

const PHONE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 };

// Runs in the page before its scripts: times every animation-frame callback, by frame, and
// notes when every canvas and formula has first drawn.
function instrument() {
  const raf = window.requestAnimationFrame.bind(window);
  window.__raf = raf;
  window.__frames = new Map();
  window.requestAnimationFrame = (cb) =>
    raf((t) => {
      const t0 = performance.now();
      cb(t);
      document.body.offsetHeight;
      window.__frames.set(t, (window.__frames.get(t) ?? 0) + performance.now() - t0);
    });
  // A figure may have no canvas and show only formulas, whose SVG MathJax draws.
  const look = () => {
    const views = document.querySelectorAll("mtp-canvas, mtp-display");
    const drawn = views.length > 0 && [...views].every((c) => c.querySelector("svg *"));
    if (drawn || document.querySelector(".mtp-error")) window.__drawnAt = performance.now();
    else raf(look);
  };
  raf(look);
}

// Runs in the page: does one action and gives its work and its time to the next frame, as the
// comment at the top says.
async function timeAction(act) {
  window.__frames.clear();
  const t0 = performance.now();
  act();
  document.body.offsetHeight;
  const sync = performance.now() - t0;
  await new Promise((r) => window.__raf(() => setTimeout(r, 0)));
  const latency = performance.now() - t0;
  const frame = [...window.__frames.values()][0] ?? 0;
  return { ms: sync + frame, latencyMs: latency };
}

// Runs in the page: does one action and gives its own work and each frame's work for ms after.
async function timeAnimation([act, ms]) {
  window.__frames.clear();
  const t0 = performance.now();
  act();
  document.body.offsetHeight;
  const sync = performance.now() - t0;
  let latency = null;
  window.__raf(() => setTimeout(() => (latency = performance.now() - t0), 0));
  await new Promise((r) => setTimeout(r, ms));
  return { sync, frames: [...window.__frames.values()], latencyMs: latency ?? undefined };
}

function build(name) {
  execFileSync("uv", ["run", "mtp", "build", join(PAGES, `${name}.mtp`)], { cwd: ROOT, stdio: "pipe" });
  return pathToFileURL(join(PAGES, `build_${name}`, "index.html")).href;
}

async function run(browser, name) {
  const result = { name, loadMs: null, updates: [], notes: [] };
  let url;
  try {
    url = build(name);
  } catch (err) {
    result.error = `mtp build failed: ${String(err.stderr ?? err).trim()}`;
    return result;
  }
  const context = await browser.newContext(PHONE);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.addInitScript(instrument);
  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  try {
    await page.goto(url, { waitUntil: "commit" });
    await page.waitForFunction(() => window.__drawnAt !== undefined, null, { timeout: 15_000 });
    result.loadMs = await page.evaluate(() => window.__drawnAt);
  } catch {
    result.notes.push("the figure did not draw within 15 s");
  }
  const shown = await page.evaluate(() => [...document.querySelectorAll(".mtp-error")].map((e) => e.textContent));
  if (shown.length) result.error = shown.join("; ");
  if (result.loadMs !== null && !result.error) await drive(page, result);
  if (errors.length) result.error = [result.error, ...errors].filter(Boolean).join("; ");
  await context.close();
  return result;
}

async function drive(page, result) {
  const end = Date.now() + EXAMPLE_MS;
  const steps = [];
  const late = () => Date.now() > end;
  // Let anything the load started, such as fonts and the first resize, settle.
  await page.waitForTimeout(300);
  const found = await page.evaluate(findInteractions, MAX_SHAPES);
  // The pointer first, while the shapes found at load are still drawn: controls and clicks may
  // hide them.
  for (const s of found.sweeps) steps.push([`${s.shape === null ? "pointer" : "hover"} ${s.label}`, () => sweep(page, result, s)]);
  for (const d of found.drags) steps.push([`drag ${d.label}`, () => drag(page, result, d)]);
  for (const kind of ["slider", "button", "play", "toggle"]) {
    for (const k of found[kind]) steps.push([`${kind} ${k.label}`, () => control(page, result, kind, k)]);
  }
  for (const c of found.clicks) steps.push([`click ${c.label}`, () => tap(page, result, c)]);
  for (const t of found.terms) steps.push([`term ${t.label}`, () => term(page, result, t)]);
  result.notes.push(...found.notes);
  for (const [i, [label, step]] of steps.entries()) {
    if (late()) {
      result.notes.push(`cut short after ${EXAMPLE_MS / 1000} s: ${steps.length - i} interactions not driven`);
      break;
    }
    try {
      await step();
    } catch (err) {
      result.notes.push(`${label} could not be driven: ${err.message.split("\n")[0]}`);
    }
  }
}

// Runs in the page: every control, draggable shape, shape with on-click and canvas listening to
// the pointer, as indexes and ids the other steps find again.
function findInteractions(max) {
  const model = document.querySelector("mtp-model");
  const rt = model.runtime;
  const out = { slider: [], button: [], play: [], toggle: [], drags: [], clicks: [], sweeps: [], notes: [] };
  const live = (sel) => [...document.querySelectorAll(sel)].map((el, k) => [el, k]).filter(([el]) => !el.disabled);
  out.slider = live("mtp-slider input[type=range]").map(([el, k]) => ({ k, label: el.closest("mtp-slider").getAttribute("name") }));
  out.button = live("mtp-button button").map(([el, k]) => ({ k, label: el.closest("mtp-button").getAttribute("name") }));
  out.play = live("mtp-play > button").map(([el, k]) => ({ k, label: el.closest("mtp-play").getAttribute("name") }));
  out.toggle = live("mtp-toggle input").map(([el, k]) => ({ k, label: el.closest("mtp-toggle").getAttribute("name") }));
  const nameOf = (id) => rt.objects[id]?.name ?? `#${id}`;
  // The outermost element of each shape the pointer can act on, so a group is driven once and
  // not again through each of its members.
  const outermost = (test) =>
    [...document.querySelectorAll("mtp-canvas svg [data-mtp-id]")].filter((el) => {
      if (!test(Number(el.getAttribute("data-mtp-id")))) return false;
      const up = el.parentElement?.closest("[data-mtp-id]");
      return !up || !test(Number(up.getAttribute("data-mtp-id")));
    });
  const seen = new Set();
  const once = (els) =>
    els.filter((el) => {
      const id = el.getAttribute("data-mtp-id");
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  const drags = once(outermost((id) => model.drags.draggable(id)));
  out.drags = drags.slice(0, max).map((el) => ({ id: el.getAttribute("data-mtp-id"), label: nameOf(Number(el.getAttribute("data-mtp-id"))) }));
  if (drags.length > max) out.notes.push(`${drags.length} shapes can be dragged; the first ${max} were`);
  seen.clear();
  const clicks = once(outermost((id) => model.clicks.find(id).length > 0 && !model.drags.draggable(id)));
  out.clicks = clicks.slice(0, max).map((el) => ({ id: el.getAttribute("data-mtp-id"), label: nameOf(Number(el.getAttribute("data-mtp-id"))) }));
  if (clicks.length > max) out.notes.push(`${clicks.length} shapes have on-click; the first ${max} were tapped`);
  // Pointer listeners: a sweep across each canvas whose own on-pointermove listens, and across
  // each shape drawn with an on-enter, on-leave or on-pointermove of its own.
  const canvases = [...document.querySelectorAll("mtp-canvas")];
  const listeners = rt.objects.filter((o) => ["on-pointermove", "on-enter", "on-leave"].includes(o.kind));
  const sweeps = [];
  canvases.forEach((c, k) => {
    const id = rt.doc.names[c.getAttribute("name")];
    if (listeners.some((l) => l.kind === "on-pointermove" && l.view === id)) sweeps.push({ canvas: k, shape: null, label: c.getAttribute("name") });
  });
  const shapes = new Set(listeners.filter((l) => l.shape !== null && l.shape !== undefined).map((l) => l.shape));
  for (const id of shapes) {
    const k = canvases.findIndex((c) => c.querySelector(`svg [data-mtp-id="${id}"]`));
    if (k >= 0) sweeps.push({ canvas: k, shape: String(id), label: nameOf(id) });
    else if (!document.querySelector(`mtp-display [data-mtp-id="${id}"]`)) out.notes.push(`${nameOf(id)} has pointer listeners but is not drawn at load, so it was not driven`);
  }
  out.sweeps = sweeps.slice(0, max);
  if (sweeps.length > max) out.notes.push(`${sweeps.length} pointer sweeps found; the first ${max} were driven`);
  // Formula terms hear pointerenter, pointerleave and click on their own elements.
  const terms = [...document.querySelectorAll("mtp-display [data-mtp-id]")].filter((el) => {
    const id = Number(el.getAttribute("data-mtp-id"));
    return shapes.has(id) || model.clicks.find(id).length > 0;
  });
  out.terms = terms.slice(0, max).map((el) => ({ id: el.getAttribute("data-mtp-id"), label: nameOf(Number(el.getAttribute("data-mtp-id"))) }));
  if (terms.length > max) out.notes.push(`${terms.length} formula terms listen; the first ${max} were driven`);
  return out;
}

// A formula term: the pointer comes onto it, it is clicked, and the pointer leaves, each timed
// with the animation it starts.
async function term(page, result, { id, label }) {
  const el = `document.querySelector('mtp-display [data-mtp-id="${id}"]')`;
  const acts = [
    ["term-enter", `${el}.dispatchEvent(new PointerEvent("pointerenter", { pointerType: "touch" }))`, TOGGLE_MS],
    ["term-click", `${el}.dispatchEvent(new MouseEvent("click", { bubbles: true }))`, ANIMATION_MS],
    ["term-leave", `${el}.dispatchEvent(new PointerEvent("pointerleave", { pointerType: "touch" }))`, TOGGLE_MS],
  ];
  await page.evaluate(`${el}.scrollIntoView({ block: "center" })`);
  for (const [kind, act, ms] of acts) {
    // Drawing the formula again replaces its elements, so each act finds the term anew.
    const t = await page.evaluate(`(${timeAnimation})([() => { if (${el}) ${act}; }, ${ms}])`);
    result.updates.push({ kind, label, ms: animationCost(t.sync, t.frames), latencyMs: t.latencyMs });
  }
}

async function control(page, result, kind, { k, label }) {
  if (kind === "slider") {
    const n = await page.evaluate((k) => {
      const input = document.querySelectorAll("mtp-slider input[type=range]")[k];
      input.scrollIntoView({ block: "center" });
      return Number(input.max);
    }, k);
    for (let s = 0; s <= SLIDER_STOPS; s++) {
      const value = String(Math.round((s / SLIDER_STOPS) * n));
      const t = await page.evaluate(
        `(${timeAction})(() => { const i = document.querySelectorAll("mtp-slider input[type=range]")[${k}]; i.value = "${value}"; i.dispatchEvent(new Event("input", { bubbles: true })); })`,
      );
      result.updates.push({ kind, label, ...t });
    }
    await page.evaluate((k) => {
      document.querySelectorAll("mtp-slider input[type=range]")[k].dispatchEvent(new Event("change", { bubbles: true }));
    }, k);
    return;
  }
  const selector = { button: "mtp-button button", play: "mtp-play > button", toggle: "mtp-toggle input" }[kind];
  // A toggle is clicked twice, on and back; a play twice, to start and to pause, so it does not
  // run on under the next interaction.
  const clicks = kind === "button" ? 1 : 2;
  const ms = kind === "toggle" ? TOGGLE_MS : ANIMATION_MS;
  for (let c = 0; c < clicks; c++) {
    const t = await page.evaluate(
      `(${timeAnimation})([() => { const b = document.querySelectorAll(${JSON.stringify(selector)})[${k}]; b.scrollIntoView({ block: "center" }); b.click(); }, ${ms}])`,
    );
    if (kind === "play" && c === 1) break;
    result.updates.push({ kind, label, ms: animationCost(t.sync, t.frames), latencyMs: t.latencyMs });
  }
}

// Runs in the page: the center of a shape on screen, after bringing it into view.
function centerOf(id) {
  const el = document.querySelector(`mtp-canvas svg [data-mtp-id="${id}"]`);
  if (!el) return null;
  el.scrollIntoView({ block: "center", inline: "center" });
  const b = el.getBoundingClientRect();
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
}

// Runs in the page: the pointer events a finger gives, pressed on whatever is at the point and
// then, as the canvas holds the pointer, moved and lifted on the SVG. Chrome counts only pointer 1
// as active for an event made in the page, so setPointerCapture accepts no other id.
function installFinger() {
  window.__finger = (type, x, y, svg) => {
    const target = type === "pointerdown" ? (document.elementFromPoint(x, y) ?? svg) : svg;
    target.dispatchEvent(
      new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, pointerId: 1, pointerType: "touch", isPrimary: true }),
    );
  };
}

async function fingerPath(page, result, kind, label, svgOf, points) {
  await page.evaluate(installFinger);
  const [x0, y0] = points[0];
  await page.evaluate(`window.__svg = (${svgOf})(); window.__finger("pointerdown", ${x0}, ${y0}, window.__svg)`);
  for (const [x, y] of points.slice(1)) {
    const t = await page.evaluate(`(${timeAction})(() => window.__finger("pointermove", ${x}, ${y}, window.__svg))`);
    result.updates.push({ kind, label, ...t });
  }
  const [x1, y1] = points.at(-1);
  await page.evaluate(`window.__finger("pointerup", ${x1}, ${y1}, window.__svg)`);
  await page.waitForTimeout(100);
}

async function drag(page, result, { id, label }) {
  const at = await page.evaluate(centerOf, id);
  if (!at) return void result.notes.push(`${label} could not be dragged: it is no longer drawn`);
  // Out and around a circle of 30 px, about 6 px a step.
  const points = [[at.x, at.y]];
  for (let s = 1; s <= DRAG_STEPS; s++) {
    const a = (2 * Math.PI * s) / DRAG_STEPS;
    points.push([at.x + 30 * Math.cos(a), at.y + 30 * Math.sin(a)]);
  }
  const svgOf = `() => document.querySelector('mtp-canvas svg [data-mtp-id="${id}"]').ownerSVGElement`;
  await fingerPath(page, result, "drag", label, svgOf, points);
}

async function tap(page, result, { id, label }) {
  const at = await page.evaluate(centerOf, id);
  if (!at) return void result.notes.push(`${label} could not be tapped: it is no longer drawn`);
  await page.evaluate(installFinger);
  const svg = `document.querySelector('mtp-canvas svg [data-mtp-id="${id}"]').ownerSVGElement`;
  await page.evaluate(`window.__finger("pointerdown", ${at.x}, ${at.y}, ${svg})`);
  const t = await page.evaluate(
    `(${timeAnimation})([() => window.__finger("pointerup", ${at.x}, ${at.y}, ${svg}), ${ANIMATION_MS}])`,
  );
  result.updates.push({ kind: "click", label, ms: animationCost(t.sync, t.frames), latencyMs: t.latencyMs });
}

async function sweep(page, result, { canvas, shape, label }) {
  // A finger drawn across the canvas from edge to edge, through the shape's center when there
  // is one, else through the canvas's middle.
  const box = await page.evaluate(
    ([k, id]) => {
      const svg = document.querySelectorAll("mtp-canvas")[k].querySelector(":scope > svg");
      const el = id === null ? svg : svg.querySelector(`[data-mtp-id="${id}"]`);
      if (!el) throw new Error("it is no longer drawn");
      el.scrollIntoView({ block: "center" });
      const s = svg.getBoundingClientRect();
      const b = el.getBoundingClientRect();
      return { left: s.left + 1, right: s.right - 1, y: b.y + b.height / 2 };
    },
    [canvas, shape],
  );
  const points = [];
  for (let s = 0; s <= SWEEP_STEPS; s++) points.push([box.left + ((box.right - box.left) * s) / SWEEP_STEPS, box.y]);
  const kind = shape === null ? "pointer" : "hover";
  const svgOf = `() => document.querySelectorAll("mtp-canvas")[${canvas}].querySelector(":scope > svg")`;
  await fingerPath(page, result, kind, label, svgOf, points);
}

mkdirSync(PAGES, { recursive: true });
for (const f of readdirSync(EXAMPLES)) if (f.endsWith(".mtp")) copyFileSync(join(EXAMPLES, f), join(PAGES, f));
const wanted = process.argv.slice(2);
const names = readdirSync(EXAMPLES)
  .filter((f) => f.endsWith(".mtp") && f !== "house.mtp")
  .map((f) => f.slice(0, -4))
  .filter((n) => !wanted.length || wanted.includes(n))
  .sort();
const browser = await chromium.launch();
const results = [];
for (const name of names) {
  const r = await run(browser, name);
  results.push(r);
  process.stderr.write(`${name}: load ${r.loadMs === null ? "-" : Math.round(r.loadMs)} ms, ${r.updates.length} updates\n`);
}
await browser.close();
console.log(table(results));
process.exit(failed(results) ? 1 : 0);
