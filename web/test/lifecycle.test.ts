// A canvas's lifecycle: state -1 at page load, its on-view, state 0 and rest, and its on-rest,
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
const resting = (el: Element) => el.hasAttribute("data-mtp-rest");
const go = () => (document.querySelector(`mtp-button[name="go"] button`) as HTMLButtonElement).click();

describe("a canvas with an on-view", () => {
  it("is in state -1 at page load, not at rest and not seen", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    expect(resting(copy("v"))).toBe(false);
    expect(copy("v").hasAttribute("data-mtp-seen")).toBe(false);
  });

  it("plays its on-view when a copy first comes into view, and is at rest once it ends", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    let told = 0;
    copy("v").addEventListener("mtp-state", () => told++);
    markSeen(copy("v"));
    expect(copy("v").hasAttribute("data-mtp-seen")).toBe(true);
    pass(0.1);
    pass(0.5);
    expect(resting(copy("v"))).toBe(false);
    pass(0.6);
    expect(v("k")).toBe(4);
    expect(resting(copy("v"))).toBe(true);
    expect(told).toBe(2);
  });

  it("plays its on-rest once at rest, and a loop nothing can change keeps it at rest", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.5);
    expect(v("spin")).toBeGreaterThan(0);
    expect(resting(copy("v"))).toBe(true);
  });

  it("leaves rest when another writer changes what its on-view moved", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    go();
    pass(0.3);
    expect(v("k")).toBeGreaterThan(4);
    expect(resting(copy("v"))).toBe(false);
  });

  it("plays no on-view in a copy that comes into view once the scene has left the values at page load", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-button model="m" name="go"></mtp-button>`);
    go();
    pass(0.1);
    pass(0.3);
    markSeen(copy("v"));
    pass(1.5);
    expect(v("k")).toBe(9);
  });
});

describe("copies of a canvas", () => {
  it("each has its own page state, and one seen later plays no on-view of its own", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="v"></mtp-canvas>`);
    const [a, b] = copies("v");
    markSeen(a!);
    pass(0.1);
    pass(0.5);
    markSeen(b!);
    expect([a!.hasAttribute("data-mtp-seen"), b!.hasAttribute("data-mtp-seen")]).toEqual([true, true]);
    const k = v("k") as number;
    pass(0.1);
    // Had b's on-view started now, it would have started k again from where it is, slower.
    expect(v("k")).toBeCloseTo(k + 0.4, 5);
    pass(1);
    expect([resting(a!), resting(b!)]).toEqual([true, true]);
  });

  it("plays no on-rest in a copy while it runs from another copy", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.5);
    const spin = v("spin") as number;
    expect(spin).toBeGreaterThan(0.2);
    document.body.insertAdjacentHTML("beforeend", `<mtp-canvas model="m" name="v"></mtp-canvas>`);
    expect(resting(copies("v")[1]!)).toBe(true);
    // Its on-rest, started again, would have put spin back to 0.
    expect(v("spin")).toBe(spin);
  });
});

describe("a canvas with no on-view", () => {
  it("is at rest from the start, and plays its on-rest when the page loads, seen or not", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="plain"></mtp-canvas>`);
    expect(copy("plain").hasAttribute("data-mtp-seen")).toBe(false);
    pass(0.1);
    pass(0.5);
    expect(v("j")).toBeCloseTo(1);
  });

  it("leaves rest when its on-rest, an ordinary writer, changes its values", () => {
    page(`<mtp-canvas model="m" name="plain"></mtp-canvas>`);
    expect(resting(copy("plain"))).toBe(true);
    pass(0.1);
    pass(0.5);
    expect(resting(copy("plain"))).toBe(false);
  });
});

describe("the page", () => {
  it("is at rest while every canvas, display and readout copy on it is", () => {
    const [model] = page(`<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="bare"></mtp-canvas><mtp-readout model="m" name="r"></mtp-readout>`);
    expect(resting(copy("bare"))).toBe(true);
    expect(resting(copy("r"))).toBe(true);
    expect(resting(model)).toBe(false);
    let told = 0;
    model.addEventListener("mtp-state", () => told++);
    markSeen(copy("v"));
    pass(0.1);
    pass(1.2);
    expect(resting(model)).toBe(true);
    expect(told).toBe(1);
  });

  it("is at rest at once when no view on it has an on-view", async () => {
    const [model] = page(`<mtp-canvas model="m" name="bare"></mtp-canvas><mtp-readout model="m" name="r"></mtp-readout>`);
    await Promise.resolve();
    expect(resting(model)).toBe(true);
  });

  it("marks a readout seen when it first comes into view", () => {
    page(`<mtp-readout model="m" name="r"></mtp-readout>`);
    markSeen(copy("r"));
    expect(copy("r").hasAttribute("data-mtp-seen")).toBe(true);
  });
});
