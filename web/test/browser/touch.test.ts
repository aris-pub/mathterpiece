// Touch on an imitated phone, with real touch events sent through the Chrome DevTools Protocol
// (docs/reference.md, "Touch screens"; mtp-4hin.1).
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { cdp } from "vitest/browser";
import { type MtpModel, define } from "../../src/elements.ts";
import type { Runtime } from "../../src/runtime.ts";
import { doc } from "../helpers.ts";

define();

const session = cdp();

beforeAll(async () => {
  await session.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await session.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
});

afterAll(async () => {
  await session.send("Emulation.clearDeviceMetricsOverride");
  await session.send("Emulation.setTouchEmulationEnabled", { enabled: false });
});

const frames = (n = 2) =>
  new Promise<void>((r) => {
    const step = (k: number) => (k <= 0 ? r() : requestAnimationFrame(() => step(k - 1)));
    step(n);
  });

// The page is taller than the screen, so a finger that the figure does not hold scrolls it.
async function open(
  name: string,
  width = 390,
): Promise<{ rt: Runtime; svg: SVGSVGElement; v: (n: string, a?: string) => unknown }> {
  window.scrollTo(0, 0);
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="v" style="display: block; width: ${width}px"></mtp-canvas><div id="below" style="height: 2000px"></div>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc(name);
  const rt = model.runtime!;
  const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
  svg.style.width = `${width}px`;
  svg.style.height = `${width}px`;
  await frames();
  return { rt, svg, v: (n, a) => rt.value(rt.id(n), a ?? null) };
}

// Where a scene point is on the screen, y up. A touch is placed on the screen, the visual
// viewport, which on a phone may stand away from the page's layout viewport.
function client(svg: SVGSVGElement, x: number, y: number): [number, number] {
  const m = svg.getScreenCTM()!;
  const view = window.visualViewport!;
  return [m.a * x + m.c * -y + m.e - view.offsetLeft, m.b * x + m.d * -y + m.f - view.offsetTop];
}

async function touch(type: "touchStart" | "touchMove" | "touchEnd" | "touchCancel", at?: [number, number]): Promise<void> {
  const touchPoints = at ? [{ x: at[0], y: at[1] }] : [];
  await session.send("Input.dispatchTouchEvent", { type, touchPoints });
}

async function tap(at: [number, number]): Promise<void> {
  await touch("touchStart", at);
  await touch("touchEnd");
  await frames();
}

async function swipe(from: [number, number], to: [number, number], steps = 8): Promise<void> {
  await touch("touchStart", from);
  for (let i = 1; i <= steps; i++) {
    await frames(1);
    await touch("touchMove", [from[0] + ((to[0] - from[0]) * i) / steps, from[1] + ((to[1] - from[1]) * i) / steps]);
  }
  await touch("touchEnd");
  await frames();
}

const near = (got: unknown, want: [number, number]) => {
  const [x, y] = got as [number, number];
  expect(x).toBeCloseTo(want[0], 1);
  expect(y).toBeCloseTo(want[1], 1);
};

describe("a finger on a shape that hears the pointer", () => {
  it("enters it and writes where the finger moves, without scrolling the page", async () => {
    const { svg, v } = await open("touch");
    await swipe(client(svg, -4, -6), client(svg, 4, -6.5));
    expect(v("over")).toBe(true);
    near(v("p"), [4, -6.5]);
    expect(window.scrollY).toBe(0);
  });
});

describe("a tap is a sticky hover", () => {
  it("stays entered after the finger lifts", async () => {
    const { svg, v } = await open("touch");
    await tap(client(svg, 0, -6));
    expect([v("over"), v("enters"), v("leaves")]).toEqual([true, 1, 0]);
    near(v("p"), [0, -6]);
  });

  it("leaves for another shape tapped, and for empty canvas", async () => {
    const { svg, v } = await open("touch");
    await tap(client(svg, 0, -6));
    await tap(client(svg, 6, 0));
    expect([v("over"), v("leaves"), v("on-other")]).toEqual([false, 1, true]);
    await tap(client(svg, 3, -2));
    expect(v("on-other")).toBe(false);
  });

  it("leaves for a tap outside the canvas", async () => {
    const { svg, v } = await open("touch");
    await tap(client(svg, 0, -6));
    const below = document.querySelector("#below")!.getBoundingClientRect();
    await tap([below.left + 100, below.top + 100]);
    expect([v("over"), v("leaves")]).toEqual([false, 1]);
  });

  it("follows the finger from shape to shape while it is down, and keeps the last", async () => {
    const { svg, v } = await open("touch");
    await swipe(client(svg, 4, -6), client(svg, 6, 0));
    expect([v("over"), v("enters"), v("leaves"), v("on-other")]).toEqual([false, 1, 1, true]);
  });
});

describe("a tap alternative to every drag", () => {
  const selected = (rt: Runtime, name: string) =>
    document.querySelector(`[data-mtp-id="${rt.id(name)}"]`)!.classList.contains("mtp-selected");

  it("a tap selects a draggable shape, and the next tap moves it there", async () => {
    const { rt, svg, v } = await open("touch");
    await tap(client(svg, 0, 4));
    expect(selected(rt, "knob")).toBe(true);
    expect(v("k")).toBe(0);
    await tap(client(svg, 3, -2));
    expect(v("k")).toBeCloseTo(3, 1);
    expect(selected(rt, "knob")).toBe(false);
    // The selection has ended: another tap moves nothing.
    await tap(client(svg, -2, -2));
    expect(v("k")).toBeCloseTo(3, 1);
  });

  it("the move keeps the drag's clamps and plays its on-dragstart and on-dragend", async () => {
    const { svg, v } = await open("touch");
    await tap(client(svg, -6, 0));
    expect(v("started")).toBe(0);
    await tap(client(svg, 3, -2));
    near([v("dot", "x"), v("dot", "y")], [-3, -2]);
    expect(v("started")).toBe(1);
    expect(v("ended")).toBe(1);
  });

  it("tapping the selected shape again, or outside the canvas, ends the selection", async () => {
    const { rt, svg, v } = await open("touch");
    await tap(client(svg, 0, 4));
    await tap(client(svg, 0, 4));
    expect(selected(rt, "knob")).toBe(false);
    await tap(client(svg, 3, -2));
    expect(v("k")).toBe(0);
    await tap(client(svg, 0, 4));
    const below = document.querySelector("#below")!.getBoundingClientRect();
    await tap([below.left + 100, below.top + 100]);
    expect(selected(rt, "knob")).toBe(false);
    await tap(client(svg, 3, -2));
    expect(v("k")).toBe(0);
  });

  it("a shape with an on-click and an on-drag plays the click and is selected", async () => {
    const { rt, svg, v } = await open("touch");
    await tap(client(svg, 0, 8));
    expect(v("clicked")).toBe(1);
    expect(selected(rt, "both")).toBe(true);
    await tap(client(svg, 3, -2));
    near([v("both", "x"), v("both", "y")], [3, -2]);
    expect(v("clicked")).toBe(1);
  });

  it("a finger still drags", async () => {
    const { rt, svg, v } = await open("touch");
    await swipe(client(svg, 0, 4), client(svg, 5, 4));
    expect(v("k")).toBeCloseTo(5, 1);
    expect(selected(rt, "knob")).toBe(false);
  });

  it("shows the selection with a ring in BRAIID's colour for what the reader acts on", async () => {
    const { rt, svg } = await open("touch");
    document.body.style.setProperty("--border-action", "rgb(1, 2, 3)");
    const el = () => document.querySelector(`[data-mtp-id="${rt.id("knob")}"]`)!;
    expect(getComputedStyle(el()).filter).toBe("none");
    await tap(client(svg, 0, 4));
    expect(getComputedStyle(el()).filter).toContain("drop-shadow(rgb(1, 2, 3)");
    document.body.style.removeProperty("--border-action");
  });
});

describe("touch targets", () => {
  it("a press within 22 pixels of a shape counts as on it", async () => {
    const { svg, v } = await open("touch");
    // The rect other is 2 units, 39 pixels, across, from x 5 to 7: 0.75 units is 15 pixels.
    await tap(client(svg, 7.75, 0));
    expect(v("on-other")).toBe(true);
  });

  it("a press further off counts as on nothing", async () => {
    const { svg, v } = await open("touch");
    await tap(client(svg, 8.6, 0));
    expect(v("on-other")).toBe(false);
  });

  it("the mouse stays exact", async () => {
    const { svg, v } = await open("touch");
    const [x, y] = client(svg, 7.75, 0);
    await session.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await frames();
    expect(v("on-other")).toBe(false);
    const [x2, y2] = client(svg, 6, 0);
    await session.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x2, y: y2 });
    await frames();
    expect(v("on-other")).toBe(true);
    await session.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1, y: 600 });
  });
});

describe("a canvas wider than the screen", () => {
  // As replicas/replica-momentum-damping.mtp on a phone: the canvas is 463 pixels wide on a
  // screen 390 across, so the page can also move sideways under a finger.
  it("a press on the band enters it, and the finger moving along it writes, without moving the page", async () => {
    const { svg, v } = await open("touch", 463);
    document.querySelector("mtp-canvas")!.scrollIntoView({ block: "center" });
    await frames();
    const [x0, y0] = [window.scrollX, window.scrollY];
    await swipe(client(svg, -6.4, -6), client(svg, -3.2, -6));
    expect(v("over")).toBe(true);
    near(v("p"), [-3.2, -6]);
    expect([window.scrollX, window.scrollY]).toEqual([x0, y0]);
  });

  it("a press keeps its enter when the browser then cancels the finger", async () => {
    const { svg, v } = await open("touch", 463);
    await touch("touchStart", client(svg, -6.4, -6));
    await touch("touchCancel");
    await frames();
    expect([v("over"), v("enters"), v("leaves")]).toEqual([true, 1, 0]);
    near(v("p"), [-6.4, -6]);
  });
});

describe("page scrolling", () => {
  it("a finger on empty canvas scrolls the page", async () => {
    const { svg } = await open("touch");
    expect(svg.style.touchAction).toBe("");
    await swipe(client(svg, 3, -2), client(svg, 3, 6));
    expect(window.scrollY).toBeGreaterThan(20);
  });

  it("the shapes the figure needs the finger for keep it, and so does a press near one", async () => {
    for (const [x, y] of [[0, -6], [6, 0], [0, 4], [-6, 0], [0, 8], [7.75, 0]] as [number, number][]) {
      const { svg } = await open("touch");
      await swipe(client(svg, x, y), client(svg, x, y + 6));
      expect(window.scrollY).toBe(0);
    }
  });

  it("a canvas whose own on-pointermove listens keeps the finger everywhere", async () => {
    const { svg } = await open("pointer");
    expect(svg.style.touchAction).toBe("none");
  });
});

describe("listeners tied to a view", () => {
  // mtp-2juu.1: in-views draws knob and dot in left and right, their listeners tied to left. In
  // right they take no finger: a swipe on them scrolls the page, and a near miss is a miss.
  async function both(): Promise<{ rt: Runtime; left: SVGSVGElement; right: SVGSVGElement; v: (n: string, a?: string) => unknown }> {
    window.scrollTo(0, 0);
    const style = "display: block; width: 390px";
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="left" style="${style}"></mtp-canvas><mtp-canvas model="m" name="right" style="${style}"></mtp-canvas><div style="height: 2000px"></div>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = doc("in-views");
    const rt = model.runtime!;
    const [left, right] = [...document.querySelectorAll("mtp-canvas svg")] as SVGSVGElement[];
    for (const svg of [left!, right!]) Object.assign(svg.style, { width: "390px", height: "390px" });
    await frames();
    return { rt, left: left!, right: right!, v: (n, a) => rt.value(rt.id(n), a ?? null) };
  }

  it("a finger drags the shape in its view, and scrolls the page from it in the other", async () => {
    const { left, right, v } = await both();
    await swipe(client(right, 5, 0), client(right, 5, 6));
    expect(window.scrollY).toBeGreaterThan(20);
    expect(v("knob", "y")).toBe(0);
    window.scrollTo(0, 0);
    await frames();
    await swipe(client(left, 5, 0), client(left, 5, 3));
    expect(window.scrollY).toBe(0);
    expect(v("knob", "y") as number).toBeGreaterThan(1);
  });

  it("a press near the shape counts as on it in its view only", async () => {
    const { left, right, v } = await both();
    // dot's edge is at x -4: 0.75 units further is about 15 pixels.
    await tap(client(right, -3.25, 0));
    expect(v("entered")).toBe(0);
    await tap(client(left, -3.25, 0));
    expect(v("entered")).toBe(1);
  });
});

describe("quiet mode", () => {
  // mtp-16z: left starts quiet, and its listeners take no finger until the reader taps its hand,
  // whose target is 44 pixels across though it is drawn smaller.
  async function quiet(): Promise<{ left: SVGSVGElement; hand: HTMLButtonElement; v: (n: string, a?: string) => unknown }> {
    window.scrollTo(0, 0);
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="left" style="display: block; width: 390px"></mtp-canvas><mtp-slider model="m" name="sl"></mtp-slider><div style="height: 2000px"></div>`;
    const model = document.querySelector("mtp-model") as MtpModel;
    model.doc = doc("quiet");
    const rt = model.runtime!;
    const left = document.querySelector("mtp-canvas svg") as SVGSVGElement;
    Object.assign(left.style, { width: "390px", height: "390px" });
    await frames();
    const hand = document.querySelector("mtp-canvas .mtp-switch") as HTMLButtonElement;
    return { left, hand, v: (n, a) => rt.value(rt.id(n), a ?? null) };
  }
  const mode = () => document.querySelector("mtp-canvas")!.getAttribute("data-mtp-mode");

  it("a finger on a quiet view scrolls the page, and drags once a tap near the hand makes it live", async () => {
    const { left, hand, v } = await quiet();
    await swipe(client(left, 5, 0), client(left, 5, 6));
    expect(window.scrollY).toBeGreaterThan(20);
    expect(v("knob", "y")).toBe(0);
    window.scrollTo(0, 0);
    await frames();
    const r = hand.getBoundingClientRect();
    expect(r.width).toBeLessThan(44);
    // Off the drawn circle, inside the 44 pixel target.
    await tap([r.left + r.width / 2 - 20, r.top + r.height / 2]);
    expect(mode()).toBe("live");
    await swipe(client(left, 5, 0), client(left, 5, 3));
    expect(window.scrollY).toBe(0);
    expect(v("knob", "y") as number).toBeGreaterThan(1);
  });

  it("a tap on the cross puts it back to quiet, and the finger scrolls the page again", async () => {
    const { left, hand, v } = await quiet();
    const middle = (): [number, number] => {
      const r = hand.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2];
    };
    await tap(middle());
    expect(mode()).toBe("live");
    await tap(middle());
    expect(mode()).toBe("quiet");
    await swipe(client(left, 5, 0), client(left, 5, 6));
    expect(window.scrollY).toBeGreaterThan(20);
    expect(v("knob", "y")).toBe(0);
  });

  describe("on a canvas that pans and zooms", () => {
    // The author, 2026-11-08: a reader scrolling past must not be caught by a quiet figure, so it
    // pans and zooms only once live.
    async function roam(): Promise<{ svg: SVGSVGElement; middle: () => [number, number] }> {
      window.scrollTo(0, 0);
      document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="roam" style="display: block; width: 390px"></mtp-canvas><div style="height: 2000px"></div>`;
      (document.querySelector("mtp-model") as MtpModel).doc = doc("quiet-pan");
      const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
      Object.assign(svg.style, { width: "390px", height: "390px" });
      await frames();
      const hand = document.querySelector("mtp-canvas .mtp-switch") as HTMLButtonElement;
      const middle = (): [number, number] => {
        const r = hand.getBoundingClientRect();
        return [r.left + r.width / 2, r.top + r.height / 2];
      };
      return { svg, middle };
    }
    const box = (svg: SVGSVGElement) => svg.getAttribute("viewBox");
    const wheel = async (at: [number, number]) => {
      await session.send("Input.dispatchMouseEvent", { type: "mouseWheel", x: at[0], y: at[1], deltaX: 0, deltaY: -300 });
      await frames();
    };

    it("a swipe on it while quiet scrolls the page, and a wheel leaves its view box", async () => {
      const { svg } = await roam();
      const before = box(svg);
      await swipe(client(svg, 3, -2), client(svg, 3, 6));
      expect(window.scrollY).toBeGreaterThan(20);
      expect(box(svg)).toBe(before);
      window.scrollTo(0, 0);
      await frames();
      await wheel(client(svg, 0, 0));
      expect(box(svg)).toBe(before);
    });

    it("once live, a swipe pans it without scrolling the page, and a wheel zooms it", async () => {
      const { svg, middle } = await roam();
      const before = box(svg);
      await tap(middle());
      await wheel(client(svg, 0, 0));
      const zoomed = box(svg);
      expect(zoomed).not.toBe(before);
      window.scrollTo(0, 0);
      await frames();
      await swipe(client(svg, 3, -2), client(svg, 3, 2));
      expect(window.scrollY).toBe(0);
      expect(box(svg)).not.toBe(zoomed);
    });

    it("back to quiet, a swipe scrolls the page again", async () => {
      const { svg, middle } = await roam();
      await tap(middle());
      await tap(middle());
      const before = box(svg);
      await swipe(client(svg, 3, -2), client(svg, 3, 6));
      expect(window.scrollY).toBeGreaterThan(20);
      expect(box(svg)).toBe(before);
    });
  });
});
