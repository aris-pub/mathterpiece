import { describe, expect, it } from "vitest";
import type { Doc, Obj } from "../../src/doc.ts";
import { Runtime } from "../../src/runtime.ts";
import { draw } from "../../src/svg.ts";

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, fill: "#000000ff", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };

function text(halign: string, valign: string) {
  const objects: Obj[] = [
    { id: 0, kind: "canvas", name: "v", attrs: { "view-x": -10, "view-y": -10, "view-width": 20, "view-height": 20, transform: ID }, shows: [1] },
    { id: 1, kind: "root", name: "s", attrs: { transform: ID }, members: [2] },
    { id: 2, kind: "text", name: "t", parent: 1, attrs: { ...style, x: 0, y: 0, value: "Hello", "font-size": 2, halign, valign } },
  ];
  const doc: Doc = { mtp: 1, objects, functions: {}, names: {}, depends: {} };
  const svg = draw(new Runtime(doc), 0);
  svg.style.width = "400px";
  document.body.replaceChildren(svg);
  // The text's box in scene units: the SVG is 400 px for 20 units, with y pointing up.
  const box = svg.querySelector("text")!.getBoundingClientRect();
  const frame = svg.getBoundingClientRect();
  const unit = frame.width / 20;
  return {
    left: (box.left - frame.left) / unit - 10,
    right: (box.right - frame.left) / unit - 10,
    top: 10 - (box.top - frame.top) / unit,
    bottom: 10 - (box.bottom - frame.top) / unit,
  };
}

describe("text alignment in a real browser", () => {
  it("puts x at the start, middle or end", () => {
    expect(text("start", "bottom").left).toBeCloseTo(0, 0);
    const middle = text("middle", "bottom");
    expect((middle.left + middle.right) / 2).toBeCloseTo(0, 0);
    expect(text("end", "bottom").right).toBeCloseTo(0, 0);
  });

  it("puts y at the top, middle or baseline", () => {
    expect(text("start", "top").top).toBeLessThan(0.5);
    expect(text("start", "top").top).toBeGreaterThan(-0.5);
    const middle = text("start", "middle");
    expect(middle.top).toBeGreaterThan(0.3);
    expect(middle.bottom).toBeLessThan(-0.3);
    expect(text("start", "bottom").bottom).toBeLessThan(0);
    expect(text("start", "bottom").bottom).toBeGreaterThan(-0.8);
  });
});
