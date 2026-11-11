// drawn, the share of a shape's outline that is drawn (mtp-ggsb; docs/reference.md, "The scene
// and shapes"). The author, 2026-11-10 and 2026-11-11: the outline is drawn from its start as if
// by a pen, the fill is drawn whole, the head at the end rides at the pen, and dashes stay.
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

function drawn(share = 0.5) {
  const rt = load("drawn");
  rt.write(rt.id("d"), null, share);
  const svg = draw(rt, rt.id("v"));
  const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]:not([data-mtp-outline])`) as SVGElement;
  const outline = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"][data-mtp-outline]`) as SVGElement | null;
  const d = (n: string) => outline(n)?.getAttribute("d") ?? null;
  const marker = (e: Element, end: "start" | "end") => {
    const url = e.getAttribute(`marker-${end}`);
    return url ? svg.querySelector(url.slice(4, -1)) : null;
  };
  return { rt, svg, el, outline, d, marker };
}

// The numbers in a path's d.
const numbers = (d: string | null) => (d ?? "").match(/-?[\d.]+(e-?\d+)?/g)!.map(Number);

describe("drawn", () => {
  it("at 1 draws the shape as it is drawn without it", () => {
    const { el, outline, marker } = drawn(1);
    expect(outline("l")).toBeNull();
    expect(outline("c")).toBeNull();
    expect(el("l").style.getPropertyValue("stroke")).toBe("#000000ff");
    expect(marker(el("l"), "end")).not.toBeNull();
    expect(el("c").style.getPropertyValue("stroke")).toBe("#000000ff");
  });

  it("at 0 draws no outline and no heads, and the fill whole", () => {
    const { rt, svg, el, outline } = drawn(0);
    expect(outline("l")).toBeNull();
    expect(outline("c")).toBeNull();
    expect(el("c").style.getPropertyValue("stroke")).toBe("none");
    expect(el("c").style.getPropertyValue("fill")).toBe("#ff0000ff");
    expect(el("l").getAttribute("marker-end")).toBeNull();
    expect(svg.querySelector(`marker[id$="-${rt.id("l")}-end"]`)).toBeNull();
  });

  it("draws a line from its from toward its to, its end's head riding at the pen", () => {
    const { el, outline, d, marker } = drawn();
    expect(d("l")).toBe("M0,0L2,0");
    expect(el("l").style.getPropertyValue("stroke")).toBe("none");
    expect(el("l").getAttribute("marker-end")).toBeNull();
    expect(marker(outline("l")!, "end")!.getAttribute("orient")).toBe("auto");
    expect(marker(outline("l")!, "start")!.getAttribute("orient")).toBe("auto-start-reverse");
    expect(outline("l")!.style.getPropertyValue("fill")).toBe("none");
    expect(outline("l")!.style.getPropertyValue("stroke")).toBe("#000000ff");
  });

  it("draws a circle from angle 0, counterclockwise, over its whole fill", () => {
    const { el, d } = drawn();
    expect(d("c")).toBe("M2,0A2,2,0,0,1,-2,0");
    expect(el("c").style.getPropertyValue("fill")).toBe("#ff0000ff");
    expect(el("c").style.getPropertyValue("stroke")).toBe("none");
    expect(drawn(0.25).d("c")).toBe("M2,0A2,2,0,0,1,0,2");
    // More than half a turn is drawn in two equal halves, as an arc is.
    expect(drawn(0.75).d("c")).toBe("M2,0A2,2,0,0,1,-1.414213562,1.414213562A2,2,0,0,1,0,-2");
  });

  it("keeps the dashes of a dashed outline", () => {
    const { outline } = drawn();
    expect(outline("dashed")!.getAttribute("stroke-dasharray")).toBe("4 2");
    expect(outline("dashed")!.getAttribute("stroke-dashoffset")).toBe("1");
    expect(outline("dashed")!.getAttribute("vector-effect")).toBe("non-scaling-stroke");
  });

  it("fades the fill and the outline together, as one shape", () => {
    const { el, outline } = drawn();
    const g = el("faded").parentElement!;
    expect(g).toBe(outline("faded")!.parentElement);
    expect(g.tagName).toBe("g");
    expect(g.getAttribute("opacity")).toBe("0.5");
    expect(el("faded").getAttribute("opacity")).toBeNull();
    expect(outline("faded")!.getAttribute("opacity")).toBeNull();
  });

  it("draws no outline for a shape with no stroke", () => {
    expect(drawn().outline("bare")).toBeNull();
  });

  it("draws an ellipse from angle 0, counterclockwise", () => {
    const all = numbers(drawn().d("e"));
    const [x0, y0, rx, ry, , , sweep] = all;
    const [x1, y1] = all.slice(-2);
    expect([x0, y0, rx, ry, sweep]).toEqual([2, 0, 2, 1, 1]);
    expect(x1).toBeCloseTo(-2, 3);
    expect(y1).toBeCloseTo(0, 3);
  });

  it("draws a rect from its first corner as SVG draws it, counterclockwise", () => {
    const { d } = drawn();
    expect(d("r")).toBe("M-2,-1L2,-1L2,1");
    expect(d("rounded")!.startsWith("M-1,-1L1,-1A1,1,0,0,1,2,0")).toBe(true);
  });

  it("draws a triangle, a polyline and a polygon along their points in order", () => {
    const { d, outline, marker } = drawn();
    expect(d("t")).toBe("M0,0L3,0L3,3");
    expect(d("p")).toBe("M0,0L1,0L1,1");
    expect(marker(outline("p")!, "end")).not.toBeNull();
    expect(d("g")).toBe("M0,0L2,0L2,2");
    // A polygon closes back to its first point at the end.
    expect(drawn(0.875).d("g")).toBe("M0,0L2,0L2,2L0,2L0,1");
  });

  it("draws a curve along itself", () => {
    const [x0, y0, cx, cy, x1, y1] = numbers(drawn().d("q"));
    expect([x0, y0]).toEqual([0, 0]);
    expect(cx).toBeCloseTo(0.5, 3);
    expect(cy).toBeCloseTo(0.5, 3);
    expect(x1).toBeCloseTo(1, 3);
    expect(y1).toBeCloseTo(0.5, 3);
  });

  it("draws an arc from its from toward its to", () => {
    expect(drawn().d("a")).toBe("M0,2A2,2,0,0,1,-2,0");
  });

  it("draws a whole ring's two circles each as a circle", () => {
    expect(drawn().d("annulus")).toBe("M2,0A2,2,0,0,1,-2,0M1,0A1,1,0,0,1,-1,0");
  });

  it("draws a ring's sector along its edges", () => {
    const sector = drawn().d("sector")!;
    expect(sector.startsWith("M2,0A2,2,0,0,1,0,2L0,1.78")).toBe(true);
  });

  it("changes nothing on a text", () => {
    const { el, outline } = drawn();
    expect(outline("tx")).toBeNull();
    expect(el("tx").style.getPropertyValue("stroke")).toBe("#000000ff");
  });

  it("is moved by an animation", () => {
    const rt = load("drawn");
    new Player(rt, rt.id("on")).seek(0.5);
    const svg = draw(rt, rt.id("v"));
    expect(svg.querySelector(`[data-mtp-id="${rt.id("moved")}"][data-mtp-outline]`)!.getAttribute("d")).toBe("M0,0L2,0");
  });
});
