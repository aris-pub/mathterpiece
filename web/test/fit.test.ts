// A canvas that gives none of x, y, width and height shows the box of its shapes as the page
// first draws them, with a margin of 5% of the box's larger side on each side, and keeps that box
// (docs/spec/page-interface.md, "The view box of a canvas"). happy-dom lays nothing out, so a
// text counts here by its position; test/browser/fit.test.ts measures one.
import { beforeEach, describe, expect, it } from "vitest";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

frames.request = () => {};

let rt: Runtime;

beforeEach(() => {
  const names = ["two", "line", "point", "empty", "fixed", "later", "absent", "text", "handled", "clipped", "turned", "zooms"];
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${names.map((n) => `<mtp-canvas model="m" name="${n}"></mtp-canvas>`).join("")}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("fit");
  rt = model.runtime!;
});

const svg = (name: string) => document.querySelector(`mtp-canvas[name="${name}"] svg`)!;

// The view box as SVG has it, y down: [x, -top, width, height].
const box = (name: string) =>
  svg(name)
    .getAttribute("viewBox")!
    .split(" ")
    .map((n) => Math.round(Number(n) * 1e9) / 1e9);

// The box from [0 0] to [10 4], with a margin of 0.5, a 20th of 10, on each side.
const TWO = [-0.5, -4.5, 11, 5];

describe("a canvas with no view box of its own", () => {
  it("shows the box of its shapes, with a margin of 5% of the larger side on each side", () => {
    expect(box("two")).toEqual(TWO);
  });

  it("gives a line along an axis the same margin across it", () => {
    expect(box("line")).toEqual([-0.5, -0.5, 11, 1]);
  });

  it("shows a square 20 wide around shapes of no size", () => {
    // The point [3 4]: from -7 to 13 across, and from -6 to 14 up.
    expect(box("point")).toEqual([-7, -14, 20, 20]);
  });

  it("shows the square from -10 to 10 when it draws nothing at first", () => {
    expect(box("empty")).toEqual([-10, -10, 20, 20]);
  });

  it("keeps the box when its shapes move", () => {
    expect(box("fixed")).toEqual([-5.5, -5.5, 11, 11]);
    rt.write(rt.id("k"), null, 20);
    expect(svg("fixed").querySelector(`[data-mtp-id="${rt.id("moving")}"]`)!.getAttribute("cx")).toBe("20");
    expect(box("fixed")).toEqual([-5.5, -5.5, 11, 11]);
  });

  it("keeps the box when a shape it did not draw at first appears", () => {
    const first = box("later");
    expect(first).toEqual([-0.2, -4.2, 4.4, 4.4]);
    rt.write(rt.id("on"), null, true);
    expect(svg("later").querySelector(`[data-mtp-id="${rt.id("far")}"]`)).not.toBeNull();
    expect(box("later")).toEqual(first);
  });

  it("leaves out a shape that does not exist", () => {
    expect(box("absent")).toEqual(box("later"));
  });

  it("counts a text by its position when the page cannot measure it", () => {
    expect(box("text")).toEqual(TWO);
  });

  it("counts a fixed-size group by its position", () => {
    expect(box("handled")).toEqual(TWO);
  });

  it("counts what a clip keeps", () => {
    expect(box("clipped")).toEqual(TWO);
  });

  it("applies its transform about the center of the box", () => {
    expect(box("turned")).toEqual(TWO);
    const top = svg("turned").querySelector(":scope > g")!.getAttribute("transform");
    expect(top).not.toBe(svg("two").querySelector(":scope > g")!.getAttribute("transform"));
  });

  it("zooms and goes back to the box on a double click", () => {
    const event = new WheelEvent("wheel", { deltaY: -500 * Math.log(2), cancelable: true });
    Object.defineProperties(event, { ctrlKey: { value: true }, clientX: { value: 5 }, clientY: { value: -2 } });
    svg("zooms").dispatchEvent(event);
    expect(box("zooms")[2]).toBe(5.5);
    svg("zooms").dispatchEvent(new MouseEvent("dblclick"));
    expect(box("zooms")).toEqual(TWO);
  });

  it("follows the pointer in the box it shows", () => {
    // Without a canvas on screen, the pointer's SVG coordinates are its page coordinates: [5 -2]
    // in the SVG is [5 2] in the scene.
    const at = (type: string, x: number, y: number) =>
      svg("zooms").dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, pointerId: 1, bubbles: true }));
    const c = svg("zooms").querySelector(`[data-mtp-id="${rt.id("c")}"]`)!;
    c.dispatchEvent(new PointerEvent("pointerdown", { clientX: 2, clientY: -2, pointerId: 1, bubbles: true }));
    at("pointermove", 5, -3);
    at("pointerup", 5, -3);
    expect(rt.value(rt.id("c"), "pos")).toEqual([5, 3]);
  });
});
