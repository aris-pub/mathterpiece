// The page elements (docs/data-model.md, "On the page"; docs/reference.md, "Components" and
// "Controls").
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

/** Moves time forward by seconds, one animation frame at a time. */
function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string, file: Doc = doc("page")): [MtpModel, Runtime, (name: string, attr?: string) => unknown] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = file;
  const rt = model.runtime!;
  return [model, rt, (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

beforeEach(() => {
  queued = [];
  clock = 0;
});

describe("the model", () => {
  it("tells its views when anything changes", () => {
    const [, rt] = page(`<mtp-readout model="m" name="r"></mtp-readout>`);
    const readout = document.querySelector("mtp-readout")!;
    expect(readout.textContent).toBe("k = 0.0");
    rt.write(rt.id("k"), null, 5);
    expect(readout.textContent).toBe("k = 5.0");
  });

  it("refuses a file of another version", () => {
    page(`<mtp-readout model="m" name="r"></mtp-readout>`, { ...doc("page"), mtpc: 1 });
    expect(document.querySelector("mtp-readout .mtp-error")!.textContent).toContain("version 4");
  });
});

describe("controls", () => {
  it("a slider sets how far along its animation is", () => {
    const [, , v] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    expect(document.querySelector("mtp-slider label")!.textContent).toBe("k");
    input.value = "500";
    input.dispatchEvent(new Event("input"));
    expect(v("k")).toBe(5);
    expect(v("sl", "position")).toBe(0.5);
  });

  it("a slider shows round ticks across its range, and fills its track up to the knob", () => {
    page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const ticks = [...document.querySelectorAll("mtp-slider .mtp-ticks [data-value]")] as HTMLElement[];
    expect(ticks.map((t) => t.dataset.value)).toEqual(["0", "2", "4", "6", "8", "10"]);
    expect(ticks.map((t) => t.style.getPropertyValue("--u"))).toEqual(["0", "0.2", "0.4", "0.6", "0.8", "1"]);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    input.value = "300";
    input.dispatchEvent(new Event("input"));
    expect(input.style.getPropertyValue("--u")).toBe("0.3");
  });

  it("adds the controls' stylesheet to the page once", () => {
    define();
    expect(document.querySelectorAll("style#mtp-controls").length).toBe(1);
  });

  it("a button plays its animation over time", () => {
    const [, , v] = page(`<mtp-button model="m" name="go"></mtp-button>`);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    // The first frame starts the clock: the model times frames from when it woke.
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(2.5);
    pass(1);
    expect(v("k")).toBe(5);
  });

  it("a control's label follows the expression it is given", () => {
    const [, rt] = page(
      `<mtp-slider model="m" name="told"></mtp-slider><mtp-button model="m" name="set"></mtp-button>` +
        `<mtp-toggle model="m" name="said"></mtp-toggle>`,
    );
    const text = () => ["mtp-slider", "mtp-button", "mtp-toggle"].map((t) => document.querySelector(t)!.textContent!.trim());
    expect(text()).toEqual(["k = 0", "set 0", "on with k = 0"]);
    rt.write(rt.id("k"), null, 7);
    pass(0.1);
    expect(text()).toEqual(["k = 7", "set 7", "on with k = 7"]);
  });

  it("a slider follows its target when another writer changes it", () => {
    const [, rt] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    rt.write(rt.id("k"), null, 7);
    expect(Number(input.value) / Number(input.max)).toBeCloseTo(0.7, 2);
  });

  it("a toggle holds its own value, or writes its target", () => {
    const [, , v] = page(`<mtp-toggle model="m" name="own"></mtp-toggle><mtp-toggle model="m" name="t"></mtp-toggle>`);
    const [own, t] = [...document.querySelectorAll("mtp-toggle input")] as HTMLInputElement[];
    own!.click();
    expect(v("own", "value")).toBe(true);
    t!.click();
    expect(v("on")).toBe(true);
  });

  it("a toggle on a group's attribute shows a mixed state, and a click sets every member", () => {
    const [, rt] = page(`<mtp-toggle model="m" name="all"></mtp-toggle>`);
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    expect(input.indeterminate).toBe(true);
    input.dispatchEvent(new Event("change"));
    const lamps = rt.objects[rt.id("lamps")]!.members!;
    expect(lamps.map((m) => rt.value(m, "lit"))).toEqual([true, true]);
  });
});

describe("a canvas", () => {
  it("draws its scene and plays an on-click on a click", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`);
    const orbit = document.querySelector(`mtp-canvas [data-mtp-id="${rt.id("orbit")}"]`)!;
    expect(orbit.tagName).toBe("circle");
    orbit.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    orbit.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    pass(0.1);
    expect(v("on")).toBe(true);
  });
});

describe("a canvas's showing and hiding", () => {

  function opacityOf(rt: Runtime, name: string, canvas = "v"): number | null {
    const el = document.querySelector(`mtp-canvas[name="${canvas}"] [data-mtp-id="${rt.id(name)}"]`);
    if (!el) return null;
    const g = el.closest("[data-mtp-toggle]");
    return g ? Number(g.getAttribute("opacity")) : 1;
  }

  it("toggles a when item over the canvas's toggle-duration", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("toggle"));
    expect(opacityOf(rt, "d")).toBeNull();
    rt.write(rt.id("show"), null, true);
    pass(0.1);
    pass(0.5);
    expect(opacityOf(rt, "d")).toBeCloseTo(0.5);
    pass(1);
    expect(opacityOf(rt, "d")).toBe(1);
  });

  it("keeps a shape's element as it fades out, and the other's as it fades in and once it has", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="swap"></mtp-canvas>`, doc("toggle"));
    const el = (name: string) => document.querySelector(`mtp-canvas[name="swap"] [data-mtp-id="${rt.id(name)}"]`);
    const c = el("c");
    rt.write(rt.id("show"), null, true);
    pass(0.1);
    pass(0.5);
    expect(el("c")).toBe(c);
    expect(c!.parentElement!.hasAttribute("data-mtp-toggle")).toBe(true);
    const d = el("d");
    pass(1);
    expect(el("d")).toBe(d);
    expect(d!.parentElement!.hasAttribute("data-mtp-toggle")).toBe(false);
    expect(el("c")).toBeNull();
  });

  it("draws its items in the order they are written", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="stack"></mtp-canvas>`, doc("toggle"));
    rt.write(rt.id("show"), null, true);
    const drawn = [...document.querySelectorAll(`mtp-canvas [data-mtp-id]`)].map((el) => Number(el.getAttribute("data-mtp-id")));
    expect(drawn).toEqual([rt.id("d"), rt.id("c")]);
  });

  it("toggles one shape out and the other in when an item changes which shape it gives", () => {
    // (if show d c): the author, 2026-11-04, a canvas shows what an item gives.
    const [, rt] = page(`<mtp-canvas model="m" name="swap"></mtp-canvas>`, doc("toggle"));
    expect(opacityOf(rt, "c", "swap")).toBe(1);
    expect(opacityOf(rt, "d", "swap")).toBeNull();
    rt.write(rt.id("show"), null, true);
    pass(0.1);
    pass(0.5);
    expect(opacityOf(rt, "c", "swap")).toBeCloseTo(0.5);
    expect(opacityOf(rt, "d", "swap")).toBeCloseTo(0.5);
    pass(1);
    expect(opacityOf(rt, "c", "swap")).toBeNull();
    expect(opacityOf(rt, "d", "swap")).toBe(1);
  });

  it("shows every shape of a list an item gives", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="pair"></mtp-canvas>`, doc("toggle"));
    expect(opacityOf(rt, "c", "pair")).toBeNull();
    rt.write(rt.id("show"), null, true);
    expect(opacityOf(rt, "c", "pair")).toBe(1);
    expect(opacityOf(rt, "d", "pair")).toBe(1);
  });

  it("shows and hides at once with no transition", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="still"></mtp-canvas>`, doc("toggle"));
    rt.write(rt.id("show"), null, true);
    expect(opacityOf(rt, "d", "still")).toBe(1);
  });
});

describe("panning and zooming a canvas", () => {
  const box = (name = "v") =>
    document.querySelector(`mtp-canvas[name="${name}"] svg`)!.getAttribute("viewBox")!.split(" ").map(Number);
  const svg = (name = "v") => document.querySelector(`mtp-canvas[name="${name}"] svg`)!;
  const pointer = (type: string, x: number, y: number, id = 1, target: Element = svg()) =>
    target.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, pointerId: id, bubbles: true }));
  // happy-dom's WheelEvent keeps only the deltas, so the rest is set on the event itself.
  const wheel = (deltaY: number, ctrlKey: boolean, target: Element = svg()) => {
    const event = new WheelEvent("wheel", { deltaY, cancelable: true });
    Object.defineProperties(event, { ctrlKey: { value: ctrlKey }, clientX: { value: 0 }, clientY: { value: 0 } });
    target.dispatchEvent(event);
  };

  it("zooms about the pointer on a pinch, which comes as a wheel with ctrl held", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    expect(box()).toEqual([-10, -10, 20, 20]);
    // Without a canvas on screen the pointer's SVG coordinates are its page coordinates.
    wheel(-500 * Math.log(2), true);
    expect(box().map((n) => Math.round(n * 1e6) / 1e6)).toEqual([-5, -5, 10, 10]);
  });

  it("zooms on a plain wheel too", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    wheel(-500 * Math.log(2), false);
    expect(box().map((n) => Math.round(n * 1e6) / 1e6)).toEqual([-5, -5, 10, 10]);
  });

  const rounded = () => box().map((n) => Math.round(n * 1e6) / 1e6);

  it("pans when the reader drags where nothing is draggable", () => {
    const [, , v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    wheel(-500 * Math.log(2), false);
    pointer("pointerdown", 100, 100);
    pointer("pointermove", 164, 132);
    pointer("pointerup", 164, 132);
    // Zoomed in 2 times, 10 units over 640 pixels: the drawing follows the pointer, 1 unit right
    // and half a unit down, which moves the view box half a unit down in y.
    expect(rounded()).toEqual([-6, -5.5, 10, 10]);
    expect(v("c", "x")).toBe(0);
  });

  it("pans by moving the view box alone, without drawing the shapes again", () => {
    // Drawing every shape again on each pointer move made panning a large scene slow.
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    wheel(-500 * Math.log(2), false);
    const before = document.querySelector(`mtp-canvas[name="v"] [data-mtp-id]`);
    pointer("pointerdown", 100, 100);
    pointer("pointermove", 164, 132);
    expect(rounded()).toEqual([-6, -5.5, 10, 10]);
    expect(document.querySelector(`mtp-canvas[name="v"] [data-mtp-id]`)).toBe(before);
    pointer("pointerup", 164, 132);
  });

  it("pans only inside the view box", () => {
    // The author, 2026-11-04: the reader never sees past what the author framed.
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    pointer("pointerdown", 100, 100);
    pointer("pointermove", 164, 132);
    expect(box()).toEqual([-10, -10, 20, 20]);
    pointer("pointerup", 164, 132);
    wheel(-500 * Math.log(2), false);
    pointer("pointerdown", 0, 0);
    // Far right and up: the view box stops at the left and top edges.
    pointer("pointermove", 5000, -5000);
    pointer("pointerup", 5000, -5000);
    expect(rounded()).toEqual([-10, 0, 10, 10]);
  });

  it("zooms out no further than the view box, and in up to its bound", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    wheel(2000, false);
    expect(rounded()).toEqual([-10, -10, 20, 20]);
    for (let k = 0; k < 20; k++) wheel(-500, false);
    // By default up to 10 times closer.
    expect(rounded()[2]).toBe(2);
  });

  it("zooms up to the bound the canvas gives", () => {
    page(`<mtp-canvas model="m" name="bounded"></mtp-canvas>`, doc("view"));
    for (let k = 0; k < 20; k++) wheel(-500, false, svg("bounded"));
    expect(box("bounded").map((n) => Math.round(n * 1e6) / 1e6)[2]).toBe(5);
  });

  it("zooms without drawing the shapes again, to what a full redraw would draw", () => {
    // Drawing every shape again on each wheel step made zooming a large scene slow.
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    const canvas = document.querySelector(`mtp-canvas[name="v"]`) as unknown as { update(): void };
    const label = () => document.querySelector(`mtp-canvas[name="v"] text`)!;
    const redrawn = () => {
      const zoomed = svg().outerHTML;
      canvas.update();
      return [zoomed, svg().outerHTML];
    };
    const before = label();
    expect(before.getAttribute("font-size")).toBe(String((16 * 20) / 640));
    wheel(-500 * Math.log(2), false);
    pointer("pointerdown", -10, 0, 1);
    pointer("pointerdown", 10, 0, 2);
    pointer("pointermove", -20, 0, 1);
    pointer("pointerup", -20, 0, 1);
    pointer("pointerup", 10, 0, 2);
    expect(label()).toBe(before);
    // Text sizes are in screen pixels. The wheel zooms in 2 times and the pinch 1.5 times, so in
    // the view box's units the text is 3 times smaller.
    expect(Number(label().getAttribute("font-size"))).toBeCloseTo((16 * 20) / 640 / 3);
    const [zoomed, full] = redrawn();
    expect(zoomed).toBe(full);
    const again = label();
    svg().dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    expect(label()).toBe(again);
    const [back, fullBack] = redrawn();
    expect(back).toBe(fullBack);
    expect(label().getAttribute("font-size")).toBe(String((16 * 20) / 640));
  });

  it("lets the reader drag a shape on every canvas that draws it", () => {
    // A listener attaches to every element that draws its shape, so dot, drawn by v and by
    // fixed, can be dragged on either, and both show where it went.
    const [, , v] = page(
      `<mtp-canvas model="m" name="v"></mtp-canvas><mtp-canvas model="m" name="fixed"></mtp-canvas>`,
      doc("view"),
    );
    const dotIn = (name: string) => document.querySelector(`mtp-canvas[name="${name}"] [data-mtp-id]:last-child`)!;
    const drag = (name: string, dx: number) => {
      const dot = dotIn(name);
      pointer("pointerdown", 100, 100, 1, dot);
      pointer("pointermove", 100 + dx, 100, 1, dot);
      pointer("pointerup", 100 + dx, 100, 1, dot);
    };
    expect(v("dot", "x")).toBe(5);
    drag("fixed", 64);
    const afterFixed = v("dot", "x") as number;
    expect(afterFixed).toBeGreaterThan(5);
    drag("v", 64);
    expect(v("dot", "x") as number).toBeGreaterThan(afterFixed);
    expect(dotIn("v").getAttribute("cx")).not.toBeNull();
    expect(dotIn("v").getAttribute("cx")).toBe(dotIn("fixed").getAttribute("cx"));
  });

  it("drags a draggable shape instead of panning", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    const dot = document.querySelector(`mtp-canvas[name="v"] [data-mtp-id]:last-child`)!;
    pointer("pointerdown", 100, 100, 1, dot);
    pointer("pointermove", 164, 132, 1, dot);
    pointer("pointerup", 164, 132, 1, dot);
    expect(box()).toEqual([-10, -10, 20, 20]);
  });

  it("zooms on a two-finger pinch", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    pointer("pointerdown", -10, 0, 1);
    pointer("pointerdown", 10, 0, 2);
    pointer("pointermove", -20, 0, 1);
    pointer("pointermove", 20, 0, 2);
    pointer("pointerup", -20, 0, 1);
    pointer("pointerup", 20, 0, 2);
    // The fingers go from 20 pixels apart to 40, so the view shows half as much.
    expect(box()[2]).toBeCloseTo(10);
  });

  it("goes back to the author's view on a double click", () => {
    page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("view"));
    pointer("pointerdown", 100, 100);
    pointer("pointermove", 164, 132);
    pointer("pointerup", 164, 132);
    svg().dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    expect(box()).toEqual([-10, -10, 20, 20]);
  });

  it("does neither when the author turns them off", () => {
    page(`<mtp-canvas model="m" name="fixed"></mtp-canvas>`, doc("view"));
    wheel(-100, true, svg("fixed"));
    pointer("pointerdown", 100, 100, 1, svg("fixed"));
    pointer("pointermove", 164, 132, 1, svg("fixed"));
    expect(box("fixed")).toEqual([-10, -10, 20, 20]);
  });
});

describe("a play's bar", () => {
  // mtp-33xt: an ink play button, then one bar per step, as wide as its duration, filling as it
  // plays, and the step now playing under the bars.
  const tour = () => page(`<mtp-play model="m" name="tour"></mtp-play>`, doc("bar"));
  const button = () => document.querySelector("mtp-play .mtp-play-button") as HTMLButtonElement;
  const bars = () => [...document.querySelectorAll("mtp-play .mtp-bar")] as HTMLElement[];
  const fills = () => bars().map((b) => Number(b.style.getPropertyValue("--u")));
  const line = () => document.querySelector("mtp-play .mtp-now")?.textContent;
  const track = () => document.querySelector("mtp-play .mtp-bars") as HTMLElement;

  // happy-dom lays nothing out: the first bar takes 100 pixels and the second, three times as
  // long, 300, after a 4 pixel gap.
  function lay(): void {
    const rect = (left: number, width: number) => () => ({ left, width, right: left + width, top: 0, bottom: 4, height: 4, x: left, y: 0, toJSON: () => ({}) }) as DOMRect;
    const [a, b] = bars();
    a!.getBoundingClientRect = rect(0, 100);
    b!.getBoundingClientRect = rect(104, 300);
    track().getBoundingClientRect = rect(0, 404);
  }

  function press(type: string, x: number): void {
    track().dispatchEvent(new PointerEvent(type, { clientX: x, clientY: 2, bubbles: true, pointerId: 1, button: 0 }));
  }

  it("shows a play button, then one bar per step as wide as its duration", () => {
    tour();
    expect(button().getAttribute("aria-label")).toBe("play the tour");
    expect(bars().map((b) => b.style.flexGrow)).toEqual(["1", "3"]);
    expect(fills()).toEqual([0, 0]);
  });

  it("without (buttons true) shows one bar for the whole animation, and no line under it", () => {
    page(`<mtp-play model="m" name="whole"></mtp-play>`, doc("bar"));
    expect(bars().length).toBe(1);
    expect(line() ?? "").toBe("");
  });

  it("counts the steps at rest, and names the step playing", () => {
    const [, , v] = tour();
    expect(line()).toBe("2 steps");
    button().click();
    expect(button().getAttribute("aria-label")).toBe("pause");
    expect(v("tour", "playing")).toBe(true);
    pass(0.1);
    pass(0.5);
    expect(line()).toBe("1 / 2 · Grow");
    expect(fills()[0]).toBeCloseTo(0.5);
    expect(fills()[1]).toBe(0);
    pass(2);
    expect(line()).toBe("2 / 2");
    expect(fills()[0]).toBe(1);
    expect(fills()[1]).toBeCloseTo(0.5);
    expect(v("tour", "step")).toBe(1);
    pass(2);
    expect(fills()).toEqual([1, 1]);
    expect(v("tour", "playing")).toBe(false);
    expect(button().getAttribute("aria-label")).toBe("play the tour");
  });

  it("pauses and resumes", () => {
    const [, , v] = tour();
    button().click();
    pass(0.1);
    pass(0.5);
    button().click();
    const paused = v("k");
    pass(1);
    expect(v("k")).toBe(paused);
    button().click();
    pass(4);
    expect(v("k")).toBe(4);
  });

  it("is a slider to assistive technology, saying the step", () => {
    tour();
    expect(track().getAttribute("role")).toBe("slider");
    expect(track().getAttribute("aria-valuetext")).toBe("2 steps");
    expect(track().tabIndex).toBe(0);
  });

  it("jumps to the start of a step tapped, and plays on from there when pressed", () => {
    const [, , v] = tour();
    lay();
    press("pointerdown", 250);
    press("pointerup", 250);
    expect(v("k")).toBe(2);
    expect(line()).toBe("2 / 2");
    expect(fills()).toEqual([1, 0]);
    expect(v("tour", "playing")).toBe(false);
    button().click();
    pass(0.1);
    pass(1.5);
    expect(v("k")).toBeCloseTo(3);
  });

  it("scrubs the tour as the reader drags along the bars, forward and back", () => {
    const [, , v] = tour();
    lay();
    press("pointerdown", 10);
    press("pointermove", 50);
    expect(v("k")).toBeCloseTo(1);
    press("pointermove", 254);
    expect(v("k")).toBeCloseTo(3);
    expect(fills()[1]).toBeCloseTo(0.5);
    press("pointermove", 50);
    expect(v("k")).toBeCloseTo(1);
    press("pointerup", 50);
    expect(v("k")).toBeCloseTo(1);
    expect(v("tour", "playing")).toBe(false);
  });

  it("plays on after a drag that began while it played", () => {
    const [, , v] = tour();
    lay();
    button().click();
    pass(0.1);
    pass(0.3);
    press("pointerdown", 10);
    press("pointermove", 254);
    pass(0.5);
    expect(v("k")).toBeCloseTo(3);
    press("pointerup", 254);
    expect(v("tour", "playing")).toBe(true);
    pass(0.1);
    const from = v("k") as number;
    pass(0.6);
    // The second step moves k by 2 in 3 seconds.
    expect((v("k") as number) - from).toBeCloseTo(0.4);
  });

  describe("with a rest between steps", () => {
    // mtp-wfrs: (rest t) pauses t seconds between each pair of steps; the bars count only the
    // steps' own durations.
    const rested = () => page(`<mtp-play model="m" name="rested"></mtp-play>`, doc("bar"));

    it("draws each bar as wide as its step alone", () => {
      rested();
      expect(bars().map((b) => b.style.flexGrow)).toEqual(["1", "3"]);
    });

    it("rests between the steps with the finished one full and the next empty", () => {
      const [, , v] = rested();
      button().click();
      pass(0.1);
      pass(1.5);
      expect(v("k")).toBe(2);
      expect(fills()).toEqual([1, 0]);
      expect(line()).toBe("1 / 2 · Grow");
      expect(v("tour", "playing")).toBe(false);
      expect(v("rested", "playing")).toBe(true);
      pass(1);
      // Half a second into the second step.
      expect(v("k")).toBeCloseTo(2 + 2 * (0.5 / 3));
      expect(line()).toBe("2 / 2");
      pass(3);
      expect(v("k")).toBe(4);
      expect(v("rested", "playing")).toBe(false);
    });

    it("jumps to a step's start past the rest before it, and scrubs over the steps alone", () => {
      const [, , v] = rested();
      lay();
      press("pointerdown", 250);
      press("pointerup", 250);
      expect(v("k")).toBe(2);
      button().click();
      pass(0.1);
      pass(0.3);
      // No rest first: the step starts at once.
      expect(v("k")).toBeGreaterThan(2);
      button().click();
      press("pointerdown", 10);
      press("pointermove", 254);
      expect(v("k")).toBeCloseTo(3);
      press("pointerup", 254);
    });
  });

  it("cancels any other writer moving what the play moves", () => {
    const [, , v] = page(`<mtp-button model="m" name="go"></mtp-button><mtp-play model="m" name="tour"></mtp-play>`, doc("bar"));
    lay();
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    pass(0.1);
    pass(0.5);
    press("pointerdown", 250);
    press("pointerup", 250);
    pass(1);
    expect(v("k")).toBe(2);
  });
});

describe("a control's when", () => {
  const all = `<mtp-button model="m" name="go"></mtp-button><mtp-slider model="m" name="sl"></mtp-slider>
    <mtp-play model="m" name="run"></mtp-play><mtp-toggle model="m" name="t"></mtp-toggle>`;
  const inputs = () => [...document.querySelectorAll("mtp-button button, mtp-slider input, mtp-play button, mtp-toggle input")] as (HTMLButtonElement | HTMLInputElement)[];

  it("lets a control be triggered only while it holds, and shows it disabled otherwise", () => {
    const [, rt, v] = page(all, doc("active"));
    expect(inputs().every((el) => !el.disabled)).toBe(true);
    rt.write(rt.id("k"), null, 4);
    expect(inputs().every((el) => el.disabled)).toBe(true);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    (document.querySelector("mtp-toggle input") as HTMLInputElement).click();
    pass(0.1);
    pass(1);
    expect(v("k")).toBe(4);
    expect(v("on")).toBe(false);
    rt.write(rt.id("k"), null, 1);
    expect(inputs().every((el) => !el.disabled)).toBe(true);
  });
});

describe("a canvas drawing again", () => {
  it("shows the pointer on a shape only while it can be dragged", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("active"));
    const cursor = (name: string) => (document.querySelector(`[data-mtp-id="${rt.id(name)}"]`) as SVGElement).style.cursor;
    expect(cursor("c")).toBe("");
    rt.write(rt.id("on"), null, true);
    expect(cursor("c")).toBe("pointer");
    expect(cursor("d")).toBe("");
    rt.write(rt.id("on"), null, false);
    expect(cursor("c")).toBe("");
  });
});

describe("starting without the reader", () => {
  // mtp-9wm: on-view, and a play's autoplay.

  it("plays an on-view's animation the first time its canvas comes into view", () => {
    const [model, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("seen"));
    pass(0.5);
    expect(v("k")).toBe(0);
    model.markSeen(rt.id("v"));
    pass(1.3);
    expect(v("k")).toBeCloseTo(10);
    rt.write(rt.id("k"), null, 0);
    model.markSeen(rt.id("v"));
    pass(1.3);
    expect(v("k")).toBe(0);
  });

  it("starts a play with (autoplay) when the page loads", () => {
    const [, rt, v] = page(`<mtp-play model="m" name="now"></mtp-play>`, doc("seen"));
    expect(v("now", "playing")).toBe(true);
    pass(1.3);
    expect(v("j")).toBeCloseTo(5);
    expect(rt.value(rt.id("now"), "playing")).toBe(false);
  });

  it("starts a play with (autoplay w) the first time w comes into view", () => {
    const [model, rt, v] = page(
      `<mtp-canvas model="m" name="w"></mtp-canvas><mtp-play model="m" name="later"></mtp-play>`,
      doc("seen"),
    );
    pass(0.5);
    expect(v("m")).toBe(0);
    model.markSeen(rt.id("w"));
    pass(1.3);
    expect(v("m")).toBeCloseTo(7);
  });
});

describe("releases", () => {
  // mtp-jpj: on-release follows JS's pointerup, and on-dragend its dragend.
  const shape = (rt: Runtime, name: string) => document.querySelector(`mtp-canvas [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0) =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: 0, pointerId: 1 }));

  it("runs an on-release when the pointer is released over the shape, wherever the press began", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    at(shape(rt, "a"), "pointerdown");
    at(shape(rt, "b"), "pointerup");
    pass(0.1);
    expect(v("r")).toBe(1);
    // A click goes to the nearest shape holding both, here the scene, which has no on-click.
    expect(v("k")).toBe(0);
  });

  it("runs an on-dragend when a drag of the shape ends", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    // The canvas holds the pointer from the press on, so the move and the release reach its svg.
    const svg = document.querySelector("mtp-canvas svg")!;
    at(shape(rt, "d"), "pointerdown", 0);
    at(svg, "pointermove", 30);
    at(svg, "pointerup", 30);
    pass(0.1);
    expect(v("e")).toBe(1);
  });

  it("runs no on-dragend for a press and release with no drag between", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    const d = shape(rt, "d");
    at(d, "pointerdown");
    at(d, "pointerup");
    pass(0.1);
    expect(v("e")).toBe(0);
  });

  it("runs an on-dragstart when a drag of the shape starts, before the drag's first write", () => {
    // mtp-5opl: dragging a data point first resets an offset, then follows the pointer.
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("dragstart"));
    const svg = document.querySelector("mtp-canvas svg")!;
    at(shape(rt, "p"), "pointerdown", 0);
    expect(v("o")).toBe(3);
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 0, clientY: -2, pointerId: 1 }));
    // The drag writes y from o, so y shows o already reset.
    expect([v("o"), v("y")]).toEqual([0, 2]);
    at(svg, "pointerup", 0);
  });

  it("runs no on-dragstart on hover, or for a press and release with no move between", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("dragstart"));
    const p = shape(rt, "p");
    at(p, "pointermove");
    at(p, "pointermove", 0.5);
    pass(0.1);
    expect(v("o")).toBe(3);
    at(p, "pointerdown");
    at(p, "pointerup");
    pass(0.1);
    expect(v("o")).toBe(3);
  });

  it("runs an on-dragstart once per drag", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("dragstart"));
    const svg = document.querySelector("mtp-canvas svg")!;
    at(shape(rt, "p"), "pointerdown", 0);
    at(svg, "pointermove", 1);
    pass(0.1);
    rt.write(rt.id("o"), null, 3);
    at(svg, "pointermove", 2);
    pass(0.1);
    expect(v("o")).toBe(3);
  });

  it("the start of a drag goes up the scene tree, unless a listener stops it", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("dragstart"));
    const svg = document.querySelector("mtp-canvas svg")!;
    const drag = (name: string) => {
      at(shape(rt, name), "pointerdown", 0);
      at(svg, "pointermove", 1);
      at(svg, "pointerup", 1);
      pass(0.1);
    };
    drag("q");
    expect([v("stopped"), v("up")]).toEqual([1, 0]);
    drag("p");
    expect(v("up")).toBe(1);
    drag("r");
    expect(v("off")).toBe(0);
  });

  it("clicks the nearest shape holding both the pressed and the released one, as JS's click", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    at(shape(rt, "p1"), "pointerdown");
    at(shape(rt, "p2"), "pointerup");
    pass(0.1);
    expect(v("g")).toBe(1);
  });

  it("clicks after the pointer moved, as JS's click", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    at(shape(rt, "d"), "pointerdown", 0);
    at(document.querySelector("mtp-canvas svg")!, "pointermove", 30);
    at(shape(rt, "d"), "pointerup", 30);
    pass(0.1);
    expect(v("c")).toBe(1);
  });

  it("clicks after a pan too, as JS's click", () => {
    const [, rt, v] = page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("release"));
    at(shape(rt, "a"), "pointerdown", 0);
    at(document.querySelector("mtp-canvas svg")!, "pointermove", 30);
    at(shape(rt, "a"), "pointerup", 30);
    pass(0.1);
    expect(v("k")).toBe(1);
  });
});


describe("a compiled model given in the page", () => {
  const inPage = (text: string, id = "m-data") =>
    `<mtp-model id="m" src="#m-data"></mtp-model>` +
    `<mtp-readout model="m" name="r"></mtp-readout>` +
    `<script type="application/json" id="${id}">${text}</script>`;

  it("is read from the JSON script the model names, even one after it", async () => {
    document.body.innerHTML = inPage(JSON.stringify(doc("page")));
    await Promise.resolve();
    expect(document.querySelector("mtp-readout")!.textContent).toBe("k = 0.0");
  });

  it("shows an error when the JSON cannot be read", async () => {
    document.body.innerHTML = inPage("{ not json");
    await Promise.resolve();
    expect(document.querySelector("mtp-readout .mtp-error")!.textContent).toContain("could not read the compiled model");
  });

  it("shows an error when the page has no such script", async () => {
    document.body.innerHTML = inPage("{}", "other");
    await Promise.resolve();
    expect(document.querySelector("mtp-readout .mtp-error")!.textContent).toContain("no script with the id m-data");
  });
});

describe("the pointer over a shape", () => {
  // mtp-izob: on-enter, on-leave and on-pointermove follow JS's pointerenter, pointerleave and
  // pointermove, touch included (the author, 2026-11-06).
  const shape = (rt: Runtime, name: string) => document.querySelector(`mtp-canvas [data-mtp-id="${rt.id(name)}"]`)!;
  const svg = () => document.querySelector("mtp-canvas svg")!;
  const at = (el: Element, type: string, x = 0, y = 0, pointerType = "mouse") =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType }));
  const open = () => page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("pointer"));

  it("plays on-enter when the pointer comes onto the shape, and on-leave when it goes", () => {
    const [, rt, v] = open();
    at(shape(rt, "a"), "pointermove");
    pass(0.1);
    expect([v("entered"), v("left")]).toEqual([1, 0]);
    // Moving over the shape again enters nothing.
    at(shape(rt, "a"), "pointermove");
    at(svg(), "pointermove");
    pass(0.1);
    expect([v("entered"), v("left")]).toEqual([1, 1]);
  });

  it("enters a group from any of its members", () => {
    const [, rt, v] = open();
    at(shape(rt, "b"), "pointermove");
    at(shape(rt, "b"), "pointermove");
    pass(0.1);
    expect(v("into-g")).toBe(1);
  });

  it("leaves when the pointer leaves the canvas", () => {
    const [, rt, v] = open();
    at(shape(rt, "a"), "pointermove");
    svg().dispatchEvent(new PointerEvent("pointerleave", { pointerId: 1 }));
    pass(0.1);
    expect(v("left")).toBe(1);
  });

  it("on a touch screen, a tap enters and the shape stays entered until a press elsewhere", () => {
    // mtp-4hin.1: a finger has no hover, so a tap is a hover that stays (the author, 2026-11-07).
    const [, rt, v] = open();
    at(shape(rt, "a"), "pointerdown", 0, 0, "touch");
    pass(0.1);
    expect(v("entered")).toBe(1);
    at(shape(rt, "a"), "pointerup", 0, 0, "touch");
    svg().dispatchEvent(new PointerEvent("pointerleave", { pointerId: 1, pointerType: "touch" }));
    pass(0.1);
    expect(v("left")).toBe(0);
    at(svg(), "pointerdown", 0, 0, "touch");
    pass(0.1);
    expect(v("left")).toBe(1);
  });

  it("on-pointermove writes the pointer's position while it is over the shape", () => {
    const [, rt, v] = open();
    at(shape(rt, "a"), "pointermove", 3, -1);
    expect(v("p")).toEqual([0, 0]);
    at(shape(rt, "b"), "pointermove", 3, -1);
    expect(v("p")).toEqual([3, 1]);
  });

  it("on-pointermove on a canvas moves a shape under the pointer, within its conditions", () => {
    const [, rt, v] = open();
    at(svg(), "pointermove", 1, -4);
    expect([v("c", "x"), v("c", "y")]).toEqual([1, 4]);
    at(shape(rt, "b"), "pointermove", 6, 0);
    expect([v("c", "x"), v("c", "y")]).toEqual([2, 0]);
  });

  it("lets the pointer through a shape with pointer-events false", () => {
    const [, rt] = open();
    expect(shape(rt, "through").getAttribute("pointer-events")).toBe("none");
    expect(shape(rt, "a").hasAttribute("pointer-events")).toBe(false);
    rt.write(rt.id("through"), "pointer-events", true);
    expect(shape(rt, "through").hasAttribute("pointer-events")).toBe(false);
  });

  it("on-pointermove writes a translate in its container's frame", () => {
    const [, , v] = open();
    at(svg(), "pointermove", 4, -2);
    expect(v("h", "translate")).toEqual([2, 1]);
  });
});

describe("bubbling", () => {
  // The author, 2026-11-06: as in the DOM, a click, a release and a pointer move go up the scene
  // tree to every listener of their kind, unless one stops them with stop-propagation.
  const shape = (rt: Runtime, name: string) => document.querySelector(`mtp-canvas [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0, y = 0) =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));
  const open = () => page(`<mtp-canvas model="m" name="v"></mtp-canvas>`, doc("bubble"));
  const click = (el: Element) => {
    at(el, "pointerdown");
    at(el, "pointerup");
    pass(0.1);
  };

  it("a click reaches the shape's listener and its group's", () => {
    const [, rt, v] = open();
    click(shape(rt, "c"));
    expect([v("inner"), v("outer")]).toEqual([1, 1]);
  });

  it("a listener with stop-propagation keeps it from its group", () => {
    const [, rt, v] = open();
    click(shape(rt, "d"));
    expect([v("top"), v("outer")]).toEqual([1, 0]);
  });

  it("a release reaches the shape's listener and its group's", () => {
    const [, rt, v] = open();
    click(shape(rt, "c"));
    expect([v("r-in"), v("r-out")]).toEqual([1, 1]);
  });

  it("a pointer move reaches the canvas's listener unless a shape's stops it", () => {
    const [, rt, v] = open();
    at(shape(rt, "c"), "pointermove", 1, -2);
    expect([v("p"), v("q")]).toEqual([[0, 0], [1, 2]]);
    at(shape(rt, "d"), "pointermove", 3, -4);
    expect([v("p"), v("q")]).toEqual([[3, 4], [1, 2]]);
  });
});
