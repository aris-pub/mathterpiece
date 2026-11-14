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
    const [, rt] = page("v");
    rt.write(rt.id("show"), null, true);
    pass(0.05);
    expect(elementOf(rt, "v", "c")!.getAttribute("pointer-events")).toBe("none");
    pass(1.1);
    expect(elementOf(rt, "v", "c")!.getAttribute("pointer-events")).toBeNull();
  });
});

// The start of a canvas is on-view, then state 0, then on-ready (docs/canvas-lifecycle.md):
// on-show and on-hide play only for shapes shown or hidden after state 0 (the author,
// 2026-11-14).
describe("the start of a canvas", () => {
  it("draws a shape that state 0 shows as it is, before and after its first view", () => {
    const [, rt] = page("w");
    expect(elementOf(rt, "w", "label")).not.toBeNull();
    expect(standIns("w")).toBe(0);
    markSeen(canvasOf("w"));
    pass(0.1);
    expect(standIns("w")).toBe(0);
    expect(drawnAs(rt, "w", "label", "opacity")).toBe(1);
  });

  it("plays no on-show before state 0, so the still picture at ready has every shape state 0 shows", () => {
    const [, rt] = page("opening");
    const copy = canvasOf("opening");
    let still: { label: boolean; glow: boolean; standIns: number } | null = null;
    copy.addEventListener("mtp-state", () => {
      if (still || !copy.hasAttribute("data-mtp-ready")) return;
      const drawn = (shape: string) => elementOf(rt, "opening", shape) !== null;
      still = { label: drawn("label"), glow: drawn("glow"), standIns: standIns("opening") };
    });
    expect(elementOf(rt, "opening", "label")).not.toBeNull();
    markSeen(copy);
    pass(1.2);
    expect(copy.hasAttribute("data-mtp-ready")).toBe(true);
    expect(rt.value(rt.id("lit"), null)).toBe(true);
    expect(still).toEqual({ label: true, glow: true, standIns: 0 });
    expect(drawnAs(rt, "opening", "glow", "opacity")).toBe(1);
  });

  it("plays on-show for a shape shown after state 0, as by on-ready", () => {
    const [, rt] = page("later-on");
    expect(rt.value(rt.id("later"), null)).toBe(true);
    pass(0.5);
    expect(drawnAs(rt, "later-on", "dot", "opacity")).toBeCloseTo(0.5, 1);
    expect(standIns("later-on")).toBe(1);
  });
});

// When a play or a stepper sets a state, and while the reader drags a play's bars, shapes appear
// and disappear at once, so a state looks the same however it was reached (the author,
// 2026-11-14). The play tour shows c in step 1 and hides it in step 3, a second each.
describe("setting a state", () => {
  const withTour = (): Runtime => {
    const [, rt] = page("v");
    document.body.insertAdjacentHTML("beforeend", `<mtp-play model="m" name="tour"></mtp-play>`);
    const play = document.querySelector("mtp-play")!;
    const rect = (left: number) => () => ({ left, width: 100, right: left + 100, top: 0, bottom: 4, height: 4, x: left, y: 0, toJSON: () => ({}) }) as DOMRect;
    play.querySelectorAll<HTMLElement>(".mtp-bar").forEach((bar, k) => {
      bar.getBoundingClientRect = rect(104 * k);
    });
    track().getBoundingClientRect = () => ({ ...rect(0)(), width: 308, right: 308 }) as DOMRect;
    return rt;
  };
  const track = () => document.querySelector("mtp-play .mtp-bars") as HTMLElement;
  const pointer = (type: string, x: number) => track().dispatchEvent(new PointerEvent(type, { clientX: x, clientY: 2, bubbles: true, pointerId: 1, button: 0 }));
  const tap = (x: number) => {
    pointer("pointerdown", x);
    pointer("pointerup", x);
  };

  it("a tap on a bar sets its state with no on-show, and the steps after it play as usual", () => {
    const rt = withTour();
    tap(154);
    expect(rt.value(rt.id("show"), null)).toBe(true);
    expect(standIns("v")).toBe(0);
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(1);
    pass(0.9);
    expect(standIns("v")).toBe(0);
    // Step 3 hides c as it plays: its on-hide plays.
    pass(0.2);
    expect(rt.value(rt.id("show"), null)).toBe(false);
    expect(standIns("v")).toBe(1);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeLessThan(1);
  });

  it("setting state 0 hides at once, and step 1 then plays its on-show from nothing drawn", () => {
    const rt = withTour();
    tap(154);
    pass(0.2);
    tap(50);
    expect(rt.value(rt.id("show"), null)).toBe(true);
    expect(standIns("v")).toBe(1);
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(0);
    pass(0.5);
    expect(drawnAs(rt, "v", "c", "drawn")).toBeCloseTo(0.5, 1);
  });

  it("a drag along the bars shows and hides at once", () => {
    const rt = withTour();
    pointer("pointerdown", 10);
    pointer("pointermove", 50);
    expect(rt.value(rt.id("show"), null)).toBe(true);
    expect(standIns("v")).toBe(0);
    expect(elementOf(rt, "v", "c")).not.toBeNull();
    pointer("pointermove", 258);
    expect(rt.value(rt.id("show"), null)).toBe(false);
    expect(elementOf(rt, "v", "c")).toBeNull();
    pointer("pointermove", 50);
    expect(standIns("v")).toBe(0);
    expect(drawnAs(rt, "v", "c", "drawn")).toBe(1);
    pointer("pointerup", 50);
    expect(standIns("v")).toBe(0);
  });
});
