// A canvas with no view box counts a text by its size as the page draws it, which only a real
// browser can measure (docs/spec/page-interface.md, "The view box of a canvas").
import { describe, expect, it } from "vitest";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

const STYLE = "<style>mtp-canvas { display: block } mtp-canvas svg { display: block; width: 100%; height: auto }</style>";

function page(body: string): MtpModel {
  document.body.innerHTML = `${STYLE}<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("fit-text");
  return model;
}

const frames = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

// How far the text's box on screen is inside its canvas's on each side, in pixels.
function inside(copy: Element, model: MtpModel): { left: number; right: number; top: number; bottom: number; width: number } {
  const svg = copy.querySelector("svg")!.getBoundingClientRect();
  const t = copy.querySelector(`[data-mtp-id="${model.runtime!.id("t")}"]`)!.getBoundingClientRect();
  return { left: t.left - svg.left, right: svg.right - t.right, top: t.top - svg.top, bottom: svg.bottom - t.bottom, width: svg.width };
}

describe("a text in a canvas with no view box", () => {
  it("fits inside the box, with the margin past its end", () => {
    const model = page(`<mtp-canvas model="m" name="v" style="width: 400px"></mtp-canvas>`);
    const gaps = inside(document.querySelector("mtp-canvas")!, model);
    expect(gaps.top).toBeGreaterThan(0);
    expect(gaps.bottom).toBeGreaterThan(0);
    // The box is wider than it is high, so the margin is a 20th of its width, and the view is
    // 1.1 times the box's width: 400 * 0.05 / 1.1 pixels.
    expect(gaps.right).toBeCloseTo((400 * 0.05) / 1.1, 0);
    expect(gaps.left).toBeGreaterThan(gaps.right);
  });

  it("is worked out for each copy at its own width", () => {
    const model = page(
      `<mtp-canvas model="m" name="v" style="width: 400px"></mtp-canvas><mtp-canvas model="m" name="v" style="width: 800px"></mtp-canvas>`,
    );
    const [narrow, wide] = [...document.querySelectorAll("mtp-canvas")];
    expect(inside(narrow!, model).right).toBeCloseTo((400 * 0.05) / 1.1, 0);
    expect(inside(wide!, model).right).toBeCloseTo((800 * 0.05) / 1.1, 0);
    expect(narrow!.querySelector("svg")!.getAttribute("viewBox")).not.toBe(wide!.querySelector("svg")!.getAttribute("viewBox"));
  });

  it("is measured once the page first shows a copy that it hid at first", async () => {
    const model = page(`<div hidden><mtp-canvas model="m" name="v" style="width: 400px"></mtp-canvas></div>`);
    document.querySelector("div")!.hidden = false;
    await frames();
    expect(inside(document.querySelector("mtp-canvas")!, model).right).toBeCloseTo((400 * 0.05) / 1.1, 0);
  });

  it("counts by its position when it is too wide for any box to hold it", () => {
    page(`<mtp-canvas model="m" name="v" style="width: 100px"></mtp-canvas>`);
    // The circle, from [-1 -1] to [1 1], and the text's position, [2 0]: 3 wide and 2 high, with
    // a margin of 0.15.
    const box = document.querySelector("mtp-canvas svg")!.getAttribute("viewBox")!.split(" ").map(Number);
    expect(box.map((n) => Math.round(n * 1e9) / 1e9)).toEqual([-1.15, -1.15, 3.3, 2.3]);
  });
});
