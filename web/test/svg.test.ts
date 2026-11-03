// Drawing a canvas as SVG (docs/reference.md, "Coordinates" and "The scene and shapes").
import { describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { apply, invert } from "../src/builtins.ts";
import { draw, paintCss, viewOf } from "../src/svg.ts";

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

  it("draws dashes and line ends as SVG does, solid by default", () => {
    const [rt, svg] = drawn();
    const l = shape(svg, rt, "dashed");
    expect(l.getAttribute("stroke-dasharray")).toBe("4 2 1 2");
    expect(l.getAttribute("stroke-dashoffset")).toBe("3");
    expect(l.getAttribute("stroke-linecap")).toBe("round");
    expect(l.getAttribute("stroke-linejoin")).toBe("bevel");
    const c = shape(svg, rt, "c");
    expect(c.getAttribute("stroke-dasharray")).toBe("none");
    expect(c.getAttribute("stroke-linecap")).toBe("butt");
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

  it("draws a shape only while its exists-when holds", () => {
    // mtp-b9g0
    const [rt, svg] = drawn();
    expect(svg.querySelector(`[data-mtp-id="${rt.id("maybe")}"]`)).not.toBeNull();
    rt.write(rt.id("shown"), null, false);
    const again = draw(rt, rt.id("v"));
    expect(again.querySelector(`[data-mtp-id="${rt.id("maybe")}"]`)).toBeNull();
  });

  it("draws a scene through its own transform, its view box in the scene's own coordinates", () => {
    // mtp-y0gh: with (scale 1 -1), y points down, as in an SVG.
    const rt = new Runtime(JSON.parse(docs["./data/runtime/flipped.mtpc"] as string) as Doc);
    const svg = draw(rt, rt.id("v"));
    expect(svg.getAttribute("viewBox")).toBe("0 0 4 2");
    const c = svg.querySelector(`[data-mtp-id="${rt.id("c")}"]`)!;
    expect(c.parentElement!.getAttribute("transform")).toBe("matrix(1 0 0 1 0 0)");
    expect([c.getAttribute("cx"), c.getAttribute("cy")]).toEqual(["2", "1"]);
    // A point the pointer is at, in the SVG's units, is read back in the scene's own coordinates.
    const back = invert(viewOf(rt, rt.id("v")).toUser);
    expect(apply(back, [2, 1])).toEqual([2, 1]);
  });
});

