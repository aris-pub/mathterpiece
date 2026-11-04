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
    expect(document.querySelector("mtp-readout .mtp-error")!.textContent).toContain("version 2");
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

  it("play pauses and resumes, and shows a button per step", () => {
    const [, , v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    const buttons = document.querySelectorAll("mtp-play button");
    expect(buttons.length).toBe(3);
    const play = buttons[0] as HTMLButtonElement;
    play.click();
    expect(play.textContent).toBe("pause");
    expect(v("run", "playing")).toBe(true);
    pass(0.5);
    play.click();
    const paused = v("k");
    pass(1);
    expect(v("k")).toBe(paused);
    play.click();
    pass(2);
    expect(v("k")).toBe(4);
  });

  it("a step clicked while stopped runs that step alone", () => {
    const [, rt, v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    rt.write(rt.id("k"), null, 9);
    const second = document.querySelectorAll("mtp-play button")[2] as HTMLButtonElement;
    second.click();
    pass(0.1);
    pass(0.5);
    // The second step moves k from 9, where it is, to 4; the first step does not run.
    expect(v("k")).toBeCloseTo(6.5);
    pass(1);
    expect(v("k")).toBe(4);
    expect(v("run", "playing")).toBe(false);
  });

  it("a step clicked while playing stops the play and animates that step alone", () => {
    const [, , v] = page(`<mtp-play model="m" name="run"></mtp-play>`);
    const [play, , second] = document.querySelectorAll("mtp-play button") as NodeListOf<HTMLButtonElement>;
    play!.click();
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(1);
    second!.click();
    // The tour stops at once; the step animates on its own.
    expect(v("run", "playing")).toBe(false);
    expect(play!.textContent).not.toBe("pause");
    // The clock is already running, so no frame is needed to start it.
    pass(0.5);
    // From 1, where k was, towards 4: it does not jump to the second step's start.
    expect(v("k")).toBeCloseTo(2.5);
    pass(1);
    expect(v("k")).toBe(4);
    pass(2);
    expect(v("k")).toBe(4);
    expect(v("run", "playing")).toBe(false);
    // Its button is lit only while the step runs.
    expect(document.querySelectorAll("mtp-play button.mtp-lit").length).toBe(0);
  });

  it("a step clicked cancels any other writer moving what the play moves", () => {
    const [, , v] = page(`<mtp-button model="m" name="go"></mtp-button><mtp-play model="m" name="run"></mtp-play>`);
    (document.querySelector("mtp-button button") as HTMLButtonElement).click();
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(2.5);
    (document.querySelectorAll("mtp-play button")[2] as HTMLButtonElement).click();
    pass(0.1);
    pass(2);
    expect(v("k")).toBe(4);
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

  it("draws its items in the order they are written", () => {
    const [, rt] = page(`<mtp-canvas model="m" name="stack"></mtp-canvas>`, doc("toggle"));
    rt.write(rt.id("show"), null, true);
    const drawn = [...document.querySelectorAll(`mtp-canvas [data-mtp-id]`)].map((el) => Number(el.getAttribute("data-mtp-id")));
    expect(drawn).toEqual([rt.id("d"), rt.id("c")]);
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

