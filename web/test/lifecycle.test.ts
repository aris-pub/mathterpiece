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
const go = () => (document.querySelector(`mtp-button[name="go"] button`) as HTMLButtonElement).click();

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

  // The author, 2026-11-13: ready is a moment, not a comparison of values.
  it("stays ready whatever any writer does after", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    go();
    pass(0.3);
    expect(v("k")).toBeGreaterThan(4);
    expect(ready(copy("v"))).toBe(true);
  });

  it("plays no on-view in a copy that comes into view once the scene has left the values at page load, and is ready then", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    go();
    pass(0.1);
    pass(0.3);
    markSeen(copy("v"));
    expect(ready(copy("v"))).toBe(true);
    pass(1.5);
    expect(v("k")).toBe(9);
  });

  it("is ready when its on-view ends because another writer cancels it", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(0.3);
    expect(ready(copy("v"))).toBe(false);
    go();
    expect(ready(copy("v"))).toBe(true);
  });
});

describe("copies of a canvas", () => {
  it("each has its own page state, and one seen later plays no on-view of its own and is ready when the other's ends", () => {
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

  it("plays no on-ready in a copy while it runs from another copy", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.5);
    const spin = v("spin") as number;
    expect(spin).toBeGreaterThan(0.2);
    document.body.insertAdjacentHTML("beforeend", `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copies("v")[1]!);
    expect(ready(copies("v")[1]!)).toBe(true);
    // Its on-ready, started again, would have put spin back to 0.
    expect(v("spin")).toBe(spin);
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
  it("is ready once every canvas, display and readout copy on it is", () => {
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
