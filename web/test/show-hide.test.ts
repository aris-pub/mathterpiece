// on-show and on-hide (docs/reference.md, "Showing and hiding"; mtp-7i3j): while one plays, the
// canvas draws a stand-in in place of the shape, which the animation moves; the scene never
// changes.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type MtpCanvas, type MtpModel, define, frames, markSeen } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

/** Moves time forward by seconds, one animation frame at a time. */
function pass(seconds: number, step = 0.05): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(...canvases: string[]): [MtpModel, Runtime] {
  document.body.innerHTML =
    `<mtp-model id="m"></mtp-model>` + canvases.map((c) => `<mtp-canvas model="m" name="${c}"></mtp-canvas>`).join("");
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("show-hide");
  return [model, model.runtime!];
}

// The model times its frames from performance.now() when it wakes: here that is the test's clock,
// so every frame is exactly one step long.
vi.spyOn(performance, "now").mockImplementation(() => clock);

const canvasOf = (name: string) => document.querySelector(`mtp-canvas[name="${name}"]`) as MtpCanvas;
const elementOf = (rt: Runtime, canvas: string, shape: string) =>
  document.querySelector(`mtp-canvas[name="${canvas}"] [data-mtp-id="${rt.id(shape)}"]`);
const standIns = (canvas: string) => document.querySelectorAll(`mtp-canvas[name="${canvas}"] [data-mtp-stand-in]`).length;
const drawnAs = (rt: Runtime, canvas: string, shape: string, attr: string) => canvasOf(canvas).drawnAs(rt.id(shape), attr);

beforeEach(() => {
  queued = [];
  clock = 0;
});

describe("on-show", () => {
  it("a shape whose when turns true is drawn by a stand-in while on-show plays, then by the original", () => {
    const [, rt] = page("v");
    markSeen(canvasOf("v"));
    pass(0.05);
    expect(elementOf(rt, "v", "c")).toBeNull();
    rt.write(rt.id("show"), null, true);
    const at = rt.clock;
    // draw-on: opacity to 1 at once, drawn from 0 to 1 over a second.
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(0);
    expect(drawnAs(rt, "v", "c", "opacity")).toBe(1);
    pass(0.5);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(0.5, 1);
    expect(elementOf(rt, "v", "c")!.closest("[data-mtp-stand-in]")).not.toBeNull();
    // The scene never changes: the original keeps every attribute.
    expect(rt.value(rt.id("c"), "drawn")).toBe(1);
    expect(rt.value(rt.id("c"), "opacity")).toBe(1);
    expect(rt.clock).toBe(at);
    pass(0.6);
    expect(elementOf(rt, "v", "c")!.closest("[data-mtp-stand-in]")).toBeNull();
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(1);
    expect(elementOf(rt, "v", "c")).not.toBeNull();
    expect(elementOf(rt, "v", "c")!.closest("[data-mtp-drawn]")).toBeNull();
    expect(rt.clock).toBe(at);
  });

  it("a shape with an on-show is not faded by toggle-duration; one without still is", () => {
    const [, rt] = page("v");
    markSeen(canvasOf("v"));
    rt.write(rt.id("show"), null, true);
    pass(0.5);
    expect(elementOf(rt, "v", "c")!.closest("[data-mtp-toggle]")).toBeNull();
    const plain = elementOf(rt, "v", "plain")!.closest("[data-mtp-toggle]");
    expect(Number(plain!.getAttribute("opacity"))).toBeCloseTo(0.5, 1);
  });

  it("plays when the canvas first comes into view, and until then the shape is hidden", () => {
    const [, rt] = page("w");
    pass(0.2);
    expect(elementOf(rt, "w", "label")).toBeNull();
    markSeen(canvasOf("w"));
    expect(drawnAs(rt, "w", "label", "opacity")).toBe(0);
    pass(1);
    expect(drawnAs(rt, "w", "label", "opacity")).toBeCloseTo(0.5, 1);
    expect(rt.value(rt.id("label"), "opacity")).toBe(1);
    pass(1.1);
    expect(standIns("w")).toBe(0);
    expect(elementOf(rt, "w", "label")).not.toBeNull();
  });

  it("each canvas plays its own on-show at its own first view", () => {
    const [, rt] = page("v", "w");
    markSeen(canvasOf("v"));
    pass(0.5);
    expect(drawnAs(rt, "v", "label", "opacity")).toBeCloseTo(0.5, 1);
    expect(elementOf(rt, "w", "label")).toBeNull();
    markSeen(canvasOf("w"));
    expect(drawnAs(rt, "w", "label", "opacity")).toBe(0);
    pass(0.5);
    expect(drawnAs(rt, "v", "label", "opacity")).toBe(1);
    expect(drawnAs(rt, "w", "label", "opacity")).toBeCloseTo(0.25, 1);
  });

  it("a group passes its on-show to its members, and a member's own wins", () => {
    const [, rt] = page("pairs");
    markSeen(canvasOf("pairs"));
    rt.write(rt.id("show"), null, true);
    pass(0.5);
    expect(drawnAs(rt, "pairs", "left", "opacity")).toBeCloseTo(0.5, 1);
    expect(drawnAs(rt, "pairs", "right", "opacity")).toBeCloseTo(0.25, 1);
    pass(0.6);
    expect(drawnAs(rt, "pairs", "left", "opacity")).toBe(1);
    expect(standIns("pairs")).toBe(1);
    pass(1);
    expect(standIns("pairs")).toBe(0);
  });
});

describe("on-hide", () => {
  it("keeps drawing the shape until its animation ends", () => {
    const [, rt] = page("v");
    markSeen(canvasOf("v"));
    rt.write(rt.id("show"), null, true);
    pass(1.1);
    rt.write(rt.id("show"), null, false);
    expect(elementOf(rt, "v", "c")).not.toBeNull();
    pass(0.5);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(0.5, 1);
    expect(elementOf(rt, "v", "c")).not.toBeNull();
    expect(rt.value(rt.id("c"), "drawn")).toBe(1);
    pass(0.6);
    expect(elementOf(rt, "v", "c")).toBeNull();
    expect(drawnAs(rt, "v", "c", "drawn")).toBeNull();
  });

  it("a flip back midway starts from where the shape is as drawn", () => {
    const [, rt] = page("v");
    markSeen(canvasOf("v"));
    rt.write(rt.id("show"), null, true);
    pass(0.05);
    pass(0.5);
    const half = drawnAs(rt, "v", "c", "drawn") as number;
    rt.write(rt.id("show"), null, false);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(half, 5);
    pass(0.25);
    const lower = drawnAs(rt, "v", "c", "drawn") as number;
    expect(lower).toBeCloseTo(half * 0.75, 1);
    rt.write(rt.id("show"), null, true);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(lower, 5);
    pass(0.5);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(lower + (1 - lower) * 0.5, 1);
    pass(0.6);
    expect(standIns("v")).toBe(0);
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(1);
  });

  it("a shape that stops existing plays on-hide on a stand-in frozen as it last was", () => {
    const [, rt] = page("vanish");
    expect(elementOf(rt, "vanish", "gone")).not.toBeNull();
    rt.write(rt.id("there"), null, false);
    expect(rt.value(rt.id("gone"), "x")).toBeNull();
    expect(drawnAs(rt, "vanish", "gone", "x")).toBe(3);
    expect(drawnAs(rt, "vanish", "gone", "fill")).toBe("#00ff00ff");
    expect(elementOf(rt, "vanish", "gone")).not.toBeNull();
    pass(0.5);
    expect(drawnAs(rt, "vanish", "gone", "opacity")).toBeCloseTo(0.5, 1);
    pass(0.6);
    expect(elementOf(rt, "vanish", "gone")).toBeNull();
  });
});

describe("a stand-in's attributes follow the original's", () => {
  it("an offset slide follows the original as a writer moves it, and ends exactly on it", () => {
    const [, rt] = page("slide");
    markSeen(canvasOf("slide"));
    rt.write(rt.id("show"), null, true);
    expect(drawnAs(rt, "slide", "slid", "x")).toBe(-4);
    pass(0.5);
    const x = drawnAs(rt, "slide", "slid", "x") as number;
    expect(x).toBeCloseTo(-2, 0);
    rt.write(rt.id("k"), null, 5);
    expect(drawnAs(rt, "slide", "slid", "x")).toBeCloseTo(x + 5, 5);
    expect(rt.value(rt.id("slid"), "x")).toBe(5);
    pass(0.6);
    expect(standIns("slide")).toBe(0);
    expect(drawnAs(rt, "slide", "slid", "x")).toBe(5);
    expect(elementOf(rt, "slide", "slid")!.getAttribute("cx")).toBe("5");
  });

  it("a color blends from the animation's value to the original's", () => {
    const [, rt] = page("tint");
    markSeen(canvasOf("tint"));
    rt.write(rt.id("show"), null, true);
    expect(drawnAs(rt, "tint", "c", "stroke")).toBe("#ff0000ff");
    pass(0.5);
    const mid = drawnAs(rt, "tint", "c", "stroke") as string;
    expect(mid).not.toBe("#ff0000ff");
    expect(mid).not.toBe("#000000ff");
    pass(0.6);
    expect(drawnAs(rt, "tint", "c", "stroke")).toBe(rt.value(rt.id("c"), "stroke"));
  });

  it("a stand-in lets the pointer through to what is under it", () => {
    const [, rt] = page("w");
    markSeen(canvasOf("w"));
    pass(0.05);
    expect(elementOf(rt, "w", "label")!.getAttribute("pointer-events")).toBe("none");
    pass(2.1);
    expect(elementOf(rt, "w", "label")!.getAttribute("pointer-events")).toBeNull();
  });
});
