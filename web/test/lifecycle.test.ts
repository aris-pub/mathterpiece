// A canvas's lifecycle: state -1 at page load, its on-view, state 0 and rest, and its on-ready,
// copy by copy (docs/canvas-lifecycle.md; the author, 2026-11-13).
import { beforeEach, describe, expect, it } from "vitest";
import { type MtpModel, define, frames, markSeen } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string): [MtpModel, Runtime, (name: string, attr?: string) => unknown] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("lifecycle");
  const rt = model.runtime!;
  return [model, rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

beforeEach(() => {
  queued = [];
  clock = 0;
});

const copies = (name: string) => [...document.querySelectorAll(`[name="${name}"]`)] as HTMLElement[];
const copy = (name: string) => copies(name)[0]!;
const ready = (el: Element) => el.hasAttribute("data-mtp-ready");
const button = (name: string) => document.querySelector(`mtp-button[name="${name}"] button`) as HTMLButtonElement;

describe("a canvas with an on-view", () => {
  it("is in state -1 at page load, not ready and not seen", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    expect(ready(copy("v"))).toBe(false);
    expect(copy("v").hasAttribute("data-mtp-seen")).toBe(false);
  });

  it("plays its on-view when a copy first comes into view, and is ready once it ends", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    let told = 0;
    copy("v").addEventListener("mtp-state", () => told++);
    markSeen(copy("v"));
    expect(copy("v").hasAttribute("data-mtp-seen")).toBe(true);
    pass(0.1);
    pass(0.5);
    expect(ready(copy("v"))).toBe(false);
    pass(0.6);
    expect(v("k")).toBe(4);
    expect(ready(copy("v"))).toBe(true);
    expect(told).toBe(2);
  });

  it("plays its on-ready once ready, which may loop", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.5);
    expect(v("spin")).toBeGreaterThan(0);
  });

  it("stays ready whatever any writer does after", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    button("go").click();
    pass(0.3);
    expect(v("k")).toBeGreaterThan(4);
    expect(ready(copy("v"))).toBe(true);
  });

  // The author, 2026-11-13: an on-view has priority 1000.
  it("plays its on-view at priority 1000, which a writer the reader sets off cannot cancel", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(0.3);
    const k = rt.id("k");
    const reader = { targets: [`${k}:`], done: false, time: 0, release() {}, place() {}, seek: () => rt.write(k, null, 9) };
    model.scheduler!.start(reader as never, {}, { reader: true });
    pass(1);
    expect(v("k")).toBe(4);
  });
});

describe("the inputs of a canvas that is not ready", () => {
  it("are disabled until it is ready: a control that writes what it shows, and a listener in it", () => {
    const [rt, v] = ((r) => [r[1], r[2]] as const)(
      page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button><mtp-button model="m" name="free"></mtp-button>`),
    );
    expect(button("go").disabled).toBe(true);
    expect(button("free").disabled).toBe(false);
    expect(copy("go").hasAttribute("data-mtp-inactive")).toBe(false);
    button("go").click();
    pass(0.5);
    expect(v("k")).toBe(0);
    const circle = document.querySelector(`mtp-canvas [data-mtp-id="${rt.id("c")}"]`)!;
    circle.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    circle.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    pass(0.1);
    expect(v("j")).toBe(0);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    expect(button("go").disabled).toBe(false);
    circle.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    circle.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    pass(0.1);
    expect(v("j")).toBe(5);
  });
});

describe("copies of a canvas", () => {
  // The author, 2026-11-13: copies of one canvas reach ready together.
  it("are ready together, from the moment the on-view of one of them has ended", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="v"></mtp-canvas>`);
    const [a, b] = copies("v");
    markSeen(a!);
    pass(0.1);
    pass(1.2);
    expect([ready(a!), ready(b!)]).toEqual([true, true]);
    expect(b!.hasAttribute("data-mtp-seen")).toBe(false);
  });

  it("each has its own page state, and one seen later plays no on-view of its own", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="v"></mtp-canvas>`);
    const [a, b] = copies("v");
    markSeen(a!);
    pass(0.1);
    pass(0.5);
    markSeen(b!);
    expect([a!.hasAttribute("data-mtp-seen"), b!.hasAttribute("data-mtp-seen")]).toEqual([true, true]);
    expect(ready(b!)).toBe(false);
    const k = v("k") as number;
    pass(0.1);
    // Had b's on-view started now, it would have started k again from where it is, slower.
    expect(v("k")).toBeCloseTo(k + 0.4, 5);
    pass(1);
    expect([ready(a!), ready(b!)]).toEqual([true, true]);
  });

  it("play the canvas's on-ready once", () => {
    const [model, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="v"></mtp-canvas>`);
    const started: unknown[] = [];
    const start = model.scheduler!.start.bind(model.scheduler!);
    model.scheduler!.start = (...args: Parameters<typeof start>) => {
      started.push(args[1]);
      return start(...args);
    };
    const [a, b] = copies("v");
    markSeen(a!);
    markSeen(b!);
    pass(0.1);
    pass(1.5);
    expect(v("spin")).toBeGreaterThan(0);
    // Both copies come into view while the scene still has the values at page load, so each
    // copy's on-view is triggered, and the canvas's on-ready plays once.
    expect(started.length).toBe(3);
  });
});

describe("a canvas with no on-view", () => {
  it("is ready from the start, and plays its on-ready when the page loads, seen or not", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="plain"></mtp-canvas>`);
    expect(ready(copy("plain"))).toBe(true);
    expect(copy("plain").hasAttribute("data-mtp-seen")).toBe(false);
    pass(0.1);
    pass(0.5);
    expect(v("j")).toBeCloseTo(1);
    expect(ready(copy("plain"))).toBe(true);
  });
});

describe("the page", () => {
  it("is ready once every canvas, display and readout on it is", () => {
    const [model] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="bare"></mtp-canvas><mtp-readout model="m" name="r"></mtp-readout>`);
    expect(ready(copy("bare"))).toBe(true);
    expect(ready(copy("r"))).toBe(true);
    expect(ready(model)).toBe(false);
    let told = 0;
    model.addEventListener("mtp-state", () => told++);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    expect(ready(model)).toBe(true);
    expect(told).toBe(1);
  });

  it("is ready at once when no view on it has an on-view", async () => {
    const [model] = page(`<mtp-canvas model="m" name="bare"></mtp-canvas><mtp-readout model="m" name="r"></mtp-readout>`);
    await Promise.resolve();
    expect(ready(model)).toBe(true);
  });

  it("marks a readout seen when it first comes into view", () => {
    page(`<mtp-readout model="m" name="r"></mtp-readout>`);
    markSeen(copy("r"));
    expect(copy("r").hasAttribute("data-mtp-seen")).toBe(true);
  });

  it("fires mtp-loaded on the model when it has loaded, and no mtp-ready", () => {
    const fired: string[] = [];
    for (const name of ["mtp-loaded", "mtp-ready"]) document.addEventListener(name, () => fired.push(name));
    page(`<mtp-canvas model="m" name="bare"></mtp-canvas>`);
    expect(fired).toEqual(["mtp-loaded"]);
  });
});
