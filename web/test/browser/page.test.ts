// What only a real browser does: CSS variables restyling a token, and the pointer's screen
// position converted into the scene (docs/data-model.md, "On the page"; docs/reference.md,
// "Dragging").
import { describe, expect, it } from "vitest";
import { userEvent } from "vitest/browser";
import type { Doc } from "../../src/doc.ts";
import { type MtpModel, define } from "../../src/elements.ts";

const docs = import.meta.glob("../data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });

define();

function page(name: string, body: string): MtpModel {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = JSON.parse(docs[`../data/runtime/${name}.mtpc`] as string) as Doc;
  return model;
}

describe("on a page", () => {
  it("restyles a token through its CSS variable", () => {
    const model = page("draw", `<mtp-canvas model="m" name="v" style="--mtp-ink: rgb(255, 0, 0)"></mtp-canvas>`);
    const rt = model.runtime!;
    const b = document.querySelector(`[data-mtp-id="${rt.id("b")}"]`)!;
    expect(getComputedStyle(b).fill).toBe("rgb(255, 0, 0)");
  });

  it("draws text at its font size in screen pixels, whatever the view box", async () => {
    const model = page("draw", `<mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas>`);
    const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
    svg.style.width = "400px";
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const t = document.querySelector(`[data-mtp-id="${model.runtime!.id("t")}"]`)!;
    // The default font size is 16 screen pixels.
    expect(t.getBoundingClientRect().height).toBeGreaterThan(10);
    expect(t.getBoundingClientRect().height).toBeLessThan(30);
  });

  it("drags a shape to where the pointer is in the scene", () => {
    const model = page("page", `<mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas>`);
    const rt = model.runtime!;
    const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
    svg.style.width = "400px";
    svg.style.height = "400px";
    const dot = () => document.querySelector(`[data-mtp-id="${rt.id("dot")}"]`)!;
    const box = dot().getBoundingClientRect();
    const [x, y] = [box.left + box.width / 2, box.top + box.height / 2];
    dot().dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));
    // The view box is 20 units across 400 pixels: 20 pixels a unit, with y up.
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: x + 40, clientY: y - 20, pointerId: 1 }));
    const [px, py] = rt.value(rt.id("dot"), "pos") as number[];
    expect(px).toBeCloseTo(3);
    expect(py).toBeCloseTo(2);
  });

  it("plays an on-click on a real click, though the canvas holds the pointer to pan", async () => {
    const model = page("page", `<mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas>`);
    const rt = model.runtime!;
    const svg = document.querySelector("mtp-canvas svg") as SVGSVGElement;
    svg.style.width = "400px";
    svg.style.height = "400px";
    // Drawing replaces the shapes' elements, so the click is aimed at the SVG, where the orbit is.
    const at = document.querySelector(`[data-mtp-id="${rt.id("orbit")}"]`)!.getBoundingClientRect();
    const frame = svg.getBoundingClientRect();
    // Other circles cover the orbit's center, but not its right side.
    const position = { x: at.left + at.width * 0.85 - frame.left, y: at.top + at.height / 2 - frame.top };
    await userEvent.click(svg, { position });
    await new Promise((r) => setTimeout(r, 100));
    expect(rt.value(rt.id("on"), null)).toBe(true);
  });
});

describe("coming into view", () => {
  // mtp-9wm: an on-view plays the first time its canvas scrolls onto the screen.
  it("plays an on-view's animation once the canvas is scrolled into view", async () => {
    const model = page(
      "seen",
      `<div style="height: 3000px"></div><mtp-canvas model="m" name="v" style="display: block; width: 200px; height: 100px"></mtp-canvas>`,
    );
    const rt = model.runtime!;
    await new Promise((r) => setTimeout(r, 300));
    expect(rt.value(rt.id("k"), null)).toBe(0);
    document.querySelector("mtp-canvas")!.scrollIntoView();
    await new Promise((r) => setTimeout(r, 1500));
    expect(rt.value(rt.id("k"), null)).toBe(10);
  });
});
