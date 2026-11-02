// Drawing a canvas as SVG (docs/reference.md, "Coordinates" and "The scene and shapes").
import { describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { draw, paintCss } from "../src/svg.ts";

const docs = import.meta.glob("./data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });

function drawn(): [Runtime, SVGSVGElement] {
  const rt = new Runtime(JSON.parse(docs["./data/runtime/draw.mtpc"] as string) as Doc);
  return [rt, draw(rt, rt.id("v"))];
}

function shape(svg: SVGSVGElement, rt: Runtime, name: string): Element {
  const el = svg.querySelector(`[data-mtp-id="${rt.id(name)}"]`);
  if (!el) throw new Error(`${name} is not drawn`);
  return el;
}

describe("drawing", () => {
  it("shows the view box, with y up", () => {
    const [, svg] = drawn();
    expect(svg.getAttribute("viewBox")).toBe("-3 -3 6 6");
  });

  it("paints the scene's background", () => {
    // The SVG element's background-color; happy-dom rejects an 8-digit hex there, so the CSS
    // value is checked directly.
    const [rt] = drawn();
    expect(paintCss(rt, rt.id("s"), "background")).toBe("#ffffffff");
  });

  it("draws a circle at its position with its paint", () => {
    const [rt, svg] = drawn();
    const c = shape(svg, rt, "c");
    expect([c.getAttribute("cx"), c.getAttribute("cy"), c.getAttribute("r")]).toEqual(["1", "2", "3"]);
    expect((c as SVGElement).style.getPropertyValue("fill")).toBe("#ff0000ff");
    expect(c.getAttribute("stroke-width")).toBe("2");
    expect(c.getAttribute("vector-effect")).toBe("non-scaling-stroke");
  });

  it("draws a group's members inside its frame, and a rect around its center", () => {
    const [rt, svg] = drawn();
    const b = shape(svg, rt, "b");
    expect(b.parentElement!.getAttribute("transform")).toBe("matrix(1 0 0 1 5 0)");
    expect([b.getAttribute("x"), b.getAttribute("y")]).toEqual(["-1", "-2"]);
  });

  it("paints with a token through its CSS variable", () => {
    const [rt, svg] = drawn();
    expect((shape(svg, rt, "b") as SVGElement).style.getPropertyValue("fill")).toBe("var(--mtp-ink, #000080ff)");
  });

  it("writes text upright, anchored by its alignment", () => {
    const [rt, svg] = drawn();
    const t = shape(svg, rt, "t");
    expect(t.textContent).toBe("hi");
    expect(t.getAttribute("text-anchor")).toBe("middle");
  });

  it("leaves out a shape that is absent", () => {
    const [rt, svg] = drawn();
    expect(svg.querySelector(`[data-mtp-id="${rt.id("gone")}"]`)).toBeNull();
    rt.write(rt.id("k"), null, 2);
    expect(draw(rt, rt.id("v")).querySelector(`[data-mtp-id="${rt.id("gone")}"]`)).not.toBeNull();
  });
});
