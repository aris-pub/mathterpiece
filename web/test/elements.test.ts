// The page elements (docs/data-model.md, "On the page"; docs/reference.md, "Components" and
// "Controls").
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

  it("a button with (selected bool) says whether it is the current choice", () => {
    const [, rt] = page(`<mtp-button model="m" name="five"></mtp-button><mtp-button model="m" name="go"></mtp-button>`);
    const [five, go] = [...document.querySelectorAll("mtp-button button")] as HTMLButtonElement[];
    expect(five!.getAttribute("aria-pressed")).toBe("false");
    // A button that does not say which state is current is not a toggle button.
    expect(go!.hasAttribute("aria-pressed")).toBe(false);
    five!.click();
    pass(0.1);
    expect(five!.getAttribute("aria-pressed")).toBe("true");
    rt.write(rt.id("k"), null, 2);
    pass(0.1);
    expect(five!.getAttribute("aria-pressed")).toBe("false");
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

  // The author, 2026-11-09: a control's label may be LaTeX, (label (tex …)), typeset as a formula is.
  it("a label given as LaTeX is typeset, and follows its expression", () => {
    const file = doc("page");
    for (const name of ["told", "set", "said"]) file.objects.find((o) => o.name === name)!["label-tex"] = true;
    const [, rt] = page(
      `<mtp-slider model="m" name="told"></mtp-slider><mtp-button model="m" name="set"></mtp-button>` +
        `<mtp-toggle model="m" name="said"></mtp-toggle>`,
      file,
    );
    const maths = () => ["mtp-slider", "mtp-button", "mtp-toggle"].map((t) => document.querySelector(`${t} .mtp-label-math`));
    expect(maths().every((m) => m?.querySelector("mjx-container svg"))).toBe(true);
    expect(maths().map((m) => m!.getAttribute("aria-label"))).toEqual(["k = 0", "set 0", "on with k = 0"]);
    rt.write(rt.id("k"), null, 7);
    pass(0.1);
    expect(maths().map((m) => m!.getAttribute("aria-label"))).toEqual(["k = 7", "set 7", "on with k = 7"]);
    expect(document.querySelector("mtp-slider input")).not.toBeNull();
    expect(document.querySelector("mtp-toggle input")).not.toBeNull();
  });

  it("a slider follows its target when another writer changes it", () => {
    const [, rt] = page(`<mtp-slider model="m" name="sl"></mtp-slider>`);
    const input = document.querySelector("mtp-slider input") as HTMLInputElement;
    rt.write(rt.id("k"), null, 7);
    expect(Number(input.value) / Number(input.max)).toBeCloseTo(0.7, 2);
  });

  it("a toggle writes its target, and its value reads it", () => {
    const [, , v] = page(`<mtp-toggle model="m" name="own"></mtp-toggle><mtp-toggle model="m" name="t"></mtp-toggle>`);
    const [own, t] = [...document.querySelectorAll("mtp-toggle input")] as HTMLInputElement[];
    own!.click();
    expect([v("mine"), v("own", "value")]).toEqual([true, true]);
    t!.click();
    expect(v("on")).toBe(true);
  });

  // mtp-0lzp: a flip is a writer set off by the reader, decided as any (docs/concurrency-model.md).
  it("a toggle's flip cancels a writer of its target, and is rejected by one of a higher priority", () => {
    const [, rt, v] = page(`<mtp-toggle model="m" name="own"></mtp-toggle>`);
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    const mine = rt.id("mine");
    const flips = (priority: number) => {
      // An animation that holds mine at false from now to its end, a second from now.
      const writer = {};
      const player = {
        targets: [`${mine}:`],
        done: false,
        time: 0,
        release() {},
        seek(t: number) {
          player.time = t;
          player.done = t >= 1;
          rt.write(mine, null, false);
        },
      };
      rt.write(mine, null, false);
      const model = document.querySelector("mtp-model") as MtpModel;
      model.scheduler!.start(player as never, writer, { reader: true, priority });
      input.click();
      pass(1.5);
      return v("mine");
    };
    expect(flips(500)).toBe(true);
    expect(flips(900)).toBe(false);
    expect(input.checked).toBe(false);
  });

  it("a toggle with an animation writes its bool, then plays it", () => {
    const [, , v] = page(`<mtp-toggle model="m" name="slide"></mtp-toggle>`);
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    input.click();
    expect(v("on")).toBe(true);
    // The first frame starts the clock.
    pass(0.1);
    pass(0.5);
    expect(v("k")).toBeCloseTo(2.5);
    pass(0.6);
    expect(v("k")).toBe(5);
    input.click();
    expect(v("on")).toBe(false);
    pass(1.2);
    expect(v("k")).toBeCloseTo(0);
  });

  // The author, 2026-11-13: a toggle is a button whose effect is (move target (to (not target))
  // (duration 0)) then its own animation, so it owns its bool until that animation ends.
  it("a toggle's flip and its animation are one effect: a newer writer of its bool cancels both", () => {
    const [model, rt, v] = page(`<mtp-toggle model="m" name="slide"></mtp-toggle>`);
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    input.click();
    pass(0.1);
    pass(0.5);
    const on = rt.id("on");
    expect(model.scheduler!.ownerOf(`${on}:`)).toBe(document.querySelector("mtp-toggle"));
    const player = { targets: [`${on}:`], done: false, time: 0, release() {}, seek: () => rt.write(on, null, false) };
    model.scheduler!.start(player as never, {}, { reader: true });
    const k = v("k");
    pass(0.5);
    expect(v("k")).toBe(k);
    expect(v("on")).toBe(false);
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

  it("zooms out past the view box to a bound below 1, and pans with the view box inside", () => {
    // The author, 2026-11-08: zooming out shows more than the view box; the view box then stays
    // inside what the canvas shows.
    page(`<mtp-canvas model="m" name="wide"></mtp-canvas>`, doc("view"));
    for (let k = 0; k < 20; k++) wheel(500, false, svg("wide"));
    const shown = () => box("wide").map((n) => Math.round(n * 1e6) / 1e6);
    expect(shown()).toEqual([-20, -20, 40, 40]);
    pointer("pointerdown", 0, 0, 1, svg("wide"));
    pointer("pointermove", 5000, -5000, 1, svg("wide"));
    pointer("pointerup", 5000, -5000, 1, svg("wide"));
    // Far right and up: what is shown stops where the view box meets its right and bottom edges.
    expect(shown()).toEqual([-30, -10, 40, 40]);
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

  it("lets the reader drag a shape on each canvas that holds a drag of it", () => {
    // Both v and fixed hold an on-drag of dot in their bodies, so dot can be dragged on either,
    // and both show where it went.
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
  // mtp-9wm: on-view.

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

  it("waits for a canvas hidden by a fully transparent ancestor to be shown before counting it as in view", () => {
    // A page may hide its content at opacity 0 while it loads (Firsthand Math does); a canvas on
    // screen then is not yet seen by anyone.
    const observers: { callback: IntersectionObserverCallback; target?: Element }[] = [];
    const saved = globalThis.IntersectionObserver;
    globalThis.IntersectionObserver = class {
      callback: IntersectionObserverCallback;
      target?: Element;
      constructor(callback: IntersectionObserverCallback) {
        this.callback = callback;
        observers.push(this);
      }
      observe(el: Element) {
        this.target = el;
      }
      disconnect() {}
    } as unknown as typeof IntersectionObserver;
    try {
      document.body.innerHTML = "";
      const [, , v] = page(`<div id="wrap" style="opacity: 0"><mtp-canvas model="m" name="v"></mtp-canvas></div>`, doc("seen"));
      const watcher = observers.find((o) => o.target?.tagName === "MTP-CANVAS")!;
      watcher.callback([{ isIntersecting: true, target: watcher.target! } as IntersectionObserverEntry], watcher as unknown as IntersectionObserver);
      pass(1.3);
      expect(v("k")).toBe(0);
      (document.getElementById("wrap") as HTMLElement).style.opacity = "1";
      pass(1.5);
      expect(v("k")).toBeCloseTo(10);
    } finally {
      globalThis.IntersectionObserver = saved;
    }
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

describe("listeners inside a view", () => {
  // mtp-6k7f: a listener written inside a canvas's body hears the pointer only in that canvas, so
  // a shape drawn in two canvases reacts in the one whose body holds its listener.
  const shape = (rt: Runtime, canvas: string, name: string) =>
    document.querySelector(`mtp-canvas[name="${canvas}"] [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0, y = 0, pointerType = "mouse") =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType }));
  const open = () =>
    page(`<mtp-canvas model="m" name="left"></mtp-canvas><mtp-canvas model="m" name="right"></mtp-canvas>`, doc("in-views"));
  const drag = (el: Element, dx: number) => {
    at(el, "pointerdown", 100, 100);
    at(el, "pointermove", 100 + dx, 100);
    at(el, "pointerup", 100 + dx, 100);
  };

  it("drags the shape in its view and not in the other", () => {
    const [, rt, v] = open();
    drag(shape(rt, "right", "knob"), 64);
    expect(v("knob", "x")).toBe(5);
    drag(shape(rt, "left", "knob"), 64);
    expect(v("knob", "x") as number).toBeGreaterThan(5);
  });

  it("clicks in its view, and elsewhere the click goes on to the group's listener", () => {
    const [, rt, v] = open();
    at(shape(rt, "right", "dot"), "pointerdown");
    at(shape(rt, "right", "dot"), "pointerup");
    pass(0.1);
    expect([v("clicks"), v("outer")]).toEqual([0, 1]);
    at(shape(rt, "left", "dot"), "pointerdown");
    at(shape(rt, "left", "dot"), "pointerup");
    pass(0.1);
    expect([v("clicks"), v("outer")]).toEqual([1, 2]);
  });

  it("hears a click on a shape only in the canvas whose body holds the listener", () => {
    const [, rt, v] = open();
    at(shape(rt, "right", "pad"), "pointerdown");
    at(shape(rt, "right", "pad"), "pointerup");
    pass(0.1);
    expect([v("tapped-left"), v("tapped-right")]).toEqual([0, 1]);
    at(shape(rt, "left", "pad"), "pointerdown");
    at(shape(rt, "left", "pad"), "pointerup");
    pass(0.1);
    expect([v("tapped-left"), v("tapped-right")]).toEqual([1, 1]);
  });

  it("enters and follows the pointer in its view only", () => {
    const [, rt, v] = open();
    at(shape(rt, "right", "dot"), "pointermove", 3, -1);
    pass(0.1);
    expect([v("entered"), v("p")]).toEqual([0, [0, 0]]);
    at(shape(rt, "left", "dot"), "pointermove", 3, -1);
    pass(0.1);
    expect(v("entered")).toBe(1);
    expect(v("p")).not.toEqual([0, 0]);
  });

  it("enters on a tap in its view only", () => {
    const [, rt, v] = open();
    at(shape(rt, "right", "dot"), "pointerdown", 0, 0, "touch");
    at(shape(rt, "right", "dot"), "pointerup", 0, 0, "touch");
    pass(0.1);
    expect(v("entered")).toBe(0);
    at(shape(rt, "left", "dot"), "pointerdown", 0, 0, "touch");
    pass(0.1);
    expect(v("entered")).toBe(1);
  });

  it("shows the pointer cursor in its view only", () => {
    const [, rt] = open();
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("pointer");
    expect((shape(rt, "right", "knob") as SVGElement).style.cursor).toBe("");
  });

  it("writes a control's views into the model, which changes nothing on the page", () => {
    const [, rt] = open();
    expect(rt.objects[rt.id("b")]!.in).toEqual([rt.id("left"), rt.id("right")]);
  });
});

describe("quiet mode", () => {
  // mtp-16z: left and says have an on-live, so each starts quiet, with a switch to make it live;
  // right has none, and behaves as before. What is tied to a quiet view is put away.
  const controls: [string, string][] = [["slider", "sl"], ["play", "p"], ["button", "b"], ["toggle", "t"], ["button", "free"]];
  const open = () =>
    page(
      `<mtp-canvas model="m" name="left"></mtp-canvas><mtp-canvas model="m" name="right"></mtp-canvas>` +
        `<mtp-readout model="m" name="says"></mtp-readout>` +
        controls.map(([kind, name]) => `<mtp-${kind} model="m" name="${name}"></mtp-${kind}>`).join(""),
      doc("quiet"),
    );
  const view = (name: string) => document.querySelector(`:is(mtp-canvas, mtp-readout)[name="${name}"]`) as HTMLElement;
  const control = (name: string) => document.querySelector(`:not(mtp-canvas, mtp-readout)[name="${name}"]`) as HTMLElement;
  const toggler = (name: string) => view(name).querySelector(".mtp-switch") as HTMLButtonElement | null;
  const folded = (name: string) => control(name).hasAttribute("data-mtp-folded");
  const shape = (rt: Runtime, canvas: string, name: string) =>
    document.querySelector(`mtp-canvas[name="${canvas}"] [data-mtp-id="${rt.id(name)}"]`)!;
  const at = (el: Element, type: string, x = 0, y = 0) =>
    el.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType: "mouse" }));

  it("a view with an on-live starts quiet, with a switch; one without has neither", () => {
    open();
    expect(view("left").dataset.mtpMode).toBe("quiet");
    expect(toggler("left")!.getAttribute("aria-label")).toBe("Interactive figure: open it");
    expect(toggler("left")!.type).toBe("button");
    expect(view("right").hasAttribute("data-mtp-mode")).toBe(false);
    expect(toggler("right")).toBeNull();
  });

  it("hides the controls tied only to quiet views, and no others", () => {
    open();
    expect([folded("sl"), folded("p"), folded("t")]).toEqual([true, true, true]);
    expect([folded("b"), folded("free")]).toEqual([false, false]);
  });

  it("the switch makes the view live: its on-live plays and its controls unfold", () => {
    const [, , v] = open();
    toggler("left")!.click();
    expect(view("left").dataset.mtpMode).toBe("live");
    expect(toggler("left")!.getAttribute("aria-label")).toBe("Back to the plain figure");
    expect([folded("sl"), folded("p"), folded("t")]).toEqual([false, false, true]);
    pass(1.2);
    expect(v("k")).toBe(10);
    expect(view("right").hasAttribute("data-mtp-mode")).toBe(false);
  });

  it("the switch, pressed again, puts it back to quiet: its on-quiet plays and its controls fold", () => {
    const [, , v] = open();
    toggler("left")!.click();
    pass(1.2);
    toggler("left")!.click();
    expect(view("left").dataset.mtpMode).toBe("quiet");
    expect(folded("sl")).toBe(true);
    pass(1.2);
    expect(v("k")).toBe(0);
  });

  it("Escape on a live view puts it back to quiet", () => {
    open();
    toggler("left")!.click();
    toggler("left")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(view("left").dataset.mtpMode).toBe("quiet");
  });

  it("the listeners tied to a quiet view hear nothing in it until it is live", () => {
    const [, rt, v] = open();
    const drag = () => {
      at(shape(rt, "left", "knob"), "pointerdown", 100, 100);
      at(shape(rt, "left", "knob"), "pointermove", 164, 100);
      at(shape(rt, "left", "knob"), "pointerup", 164, 100);
    };
    drag();
    expect(v("knob", "x")).toBe(5);
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("");
    at(shape(rt, "left", "dot"), "pointerdown");
    at(shape(rt, "left", "dot"), "pointerup");
    pass(0.1);
    expect(v("clicks")).toBe(0);
    toggler("left")!.click();
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("pointer");
    drag();
    expect(v("knob", "x") as number).toBeGreaterThan(5);
  });

  // The cursor of a shape the reader can act on follows its view going live, even when nothing
  // was written or made since the view last drew.
  it("shows the pointer cursor on a shape once its view goes live, after a write while quiet", () => {
    const [, rt] = open();
    rt.write(rt.id("k"), null, 1);
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("");
    toggler("left")!.click();
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("pointer");
    toggler("left")!.click();
    expect((shape(rt, "left", "knob") as SVGElement).style.cursor).toBe("");
  });

  it("a readout keeps its text beside its switch, and goes live on its own", () => {
    const [, , v] = open();
    expect(view("says").textContent).toBe("k is 0.0");
    toggler("says")!.click();
    expect(view("left").dataset.mtpMode).toBe("quiet");
    expect(folded("t")).toBe(false);
    pass(0.1);
    expect(v("said")).toBe(1);
    expect(view("says").textContent).toBe("k is 0.0");
    expect(toggler("says")).not.toBeNull();
  });

  it("an on-live may move the view itself", () => {
    page(`<mtp-canvas model="m" name="wide"></mtp-canvas>`, doc("quiet"));
    const svg = document.querySelector("mtp-canvas svg")!;
    const width = () => Number(svg.getAttribute("viewBox")!.split(" ")[2]);
    expect(width()).toBe(20);
    (document.querySelector("mtp-canvas .mtp-switch") as HTMLButtonElement).click();
    pass(1.2);
    expect(width()).toBe(10);
  });

  describe("pan and zoom", () => {
    // roam pans and zooms but has an on-live; plain has none.
    const roam = () => {
      page(`<mtp-canvas model="m" name="roam"></mtp-canvas><mtp-canvas model="m" name="plain"></mtp-canvas>`, doc("quiet-pan"));
      return {
        svg: (name = "roam") => document.querySelector(`mtp-canvas[name="${name}"] svg`) as SVGSVGElement,
        hand: () => toggler("roam")!,
      };
    };
    const box = (svg: Element) => svg.getAttribute("viewBox")!.split(" ").map((n) => Math.round(Number(n) * 1e6) / 1e6);
    const wheel = (svg: Element) => {
      const event = new WheelEvent("wheel", { deltaY: -500 * Math.log(2), cancelable: true });
      Object.defineProperties(event, { clientX: { value: 0 }, clientY: { value: 0 } });
      svg.dispatchEvent(event);
      return event;
    };
    const finger = (svg: Element, type: string, x: number, y: number, id = 1) =>
      svg.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, pointerId: id, bubbles: true, pointerType: "touch", cancelable: true }));
    const drag = (svg: Element) => {
      finger(svg, "pointerdown", 100, 100);
      finger(svg, "pointermove", 164, 132);
      finger(svg, "pointerup", 164, 132);
    };
    const pinch = (svg: Element) => {
      finger(svg, "pointerdown", -10, 0, 1);
      finger(svg, "pointerdown", 10, 0, 2);
      finger(svg, "pointermove", -20, 0, 1);
      finger(svg, "pointermove", 20, 0, 2);
      finger(svg, "pointerup", -20, 0, 1);
      finger(svg, "pointerup", 20, 0, 2);
    };

    it("a quiet canvas ignores the wheel, and leaves it to the page", () => {
      const { svg } = roam();
      const event = wheel(svg());
      expect(event.defaultPrevented).toBe(false);
      expect(box(svg())).toEqual([-10, -10, 20, 20]);
    });

    it("a quiet canvas does not pan or pinch, and lets a finger scroll the page", () => {
      const { svg } = roam();
      expect(svg().style.touchAction).toBe("");
      drag(svg());
      pinch(svg());
      expect(box(svg())).toEqual([-10, -10, 20, 20]);
    });

    it("once live, it zooms, pans and pinches, and keeps the finger", () => {
      const { svg, hand } = roam();
      hand().click();
      expect(svg().style.touchAction).toBe("none");
      expect(wheel(svg()).defaultPrevented).toBe(true);
      expect(box(svg())).toEqual([-5, -5, 10, 10]);
      drag(svg());
      expect(box(svg())).toEqual([-6, -5.5, 10, 10]);
      svg().dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
      pinch(svg());
      expect(box(svg())[2]).toBeCloseTo(10);
    });

    it("going quiet again turns them off, and puts back the illustrator's view", () => {
      const { svg, hand } = roam();
      hand().click();
      wheel(svg());
      hand().click();
      expect(svg().style.touchAction).toBe("");
      expect(box(svg())).toEqual([-10, -10, 20, 20]);
      expect(wheel(svg()).defaultPrevented).toBe(false);
      drag(svg());
      expect(box(svg())).toEqual([-10, -10, 20, 20]);
    });

    it("a canvas with no on-live pans and zooms as before", () => {
      const { svg } = roam();
      expect(svg("plain").style.touchAction).toBe("none");
      wheel(svg("plain"));
      expect(box(svg("plain"))).toEqual([-5, -5, 10, 10]);
    });
  });
});
