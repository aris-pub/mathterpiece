// Heads on the ends of lines, polylines and arcs (mtp-brs): SVG markers, in the shape's stroke,
// sized in screen pixels by the stroke width times head-size.
import { describe, expect, it } from "vitest";
import { draw, zoom } from "../src/svg.ts";
import { load } from "./helpers.ts";

function drawn() {
  const rt = load("heads");
  const svg = draw(rt, rt.id("v"));
  const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`) as SVGElement;
  const marker = (n: string, end: "start" | "end") => {
    const url = el(n).getAttribute(`marker-${end}`);
    return url ? (svg.querySelector(url.slice(4, -1)) as SVGMarkerElement) : null;
  };
  return { rt, svg, el, marker };
}

describe("heads", () => {
  it("are markers at the ends asked for, turned along the shape", () => {
    const { marker } = drawn();
    expect(marker("vec", "end")!.getAttribute("orient")).toBe("auto");
    expect(marker("vec", "start")!.getAttribute("orient")).toBe("auto-start-reverse");
    expect(marker("turn", "end")).not.toBeNull();
    expect(marker("turn", "start")).toBeNull();
    expect(marker("path", "end")).not.toBeNull();
    expect(marker("path", "start")).not.toBeNull();
  });

  it("are drawn in the shape's stroke", () => {
    const { marker } = drawn();
    const fill = (m: SVGMarkerElement) => (m.firstElementChild as SVGElement).style.getPropertyValue("fill");
    const stroke = (m: SVGMarkerElement) => (m.firstElementChild as SVGElement).style.getPropertyValue("stroke");
    expect(fill(marker("vec", "end")!)).toBe("#ff0000ff");
    expect(stroke(marker("vec", "start")!)).toBe("#ff0000ff");
    expect(fill(marker("turn", "end")!)).toBe("#0000ffff");
  });

  it("scale with the stroke width and head-size, in screen pixels", () => {
    const { marker } = drawn();
    const width = (m: SVGMarkerElement) => Number(m.getAttribute("markerWidth"));
    expect(width(marker("big", "end")!) / width(marker("vec", "end")!)).toBeCloseTo(1.5);
    expect(marker("vec", "end")!.getAttribute("markerUnits")).toBe("userSpaceOnUse");
  });

  it("are resized when the reader zooms", () => {
    const { rt, svg, marker } = drawn();
    const before = Number(marker("vec", "end")!.getAttribute("markerWidth"));
    zoom(rt, rt.id("v"), svg, { scale: 2, dx: 0, dy: 0 });
    expect(Number(marker("vec", "end")!.getAttribute("markerWidth"))).toBeCloseTo(before / 2);
  });

  it("are not drawn with no stroke, or when the head is none", () => {
    const { rt, svg, marker } = drawn();
    expect(marker("bare", "end")).toBeNull();
    expect(marker("maybe", "end")).not.toBeNull();
    rt.write(rt.id("on"), null, false);
    const again = draw(rt, rt.id("v"));
    expect(again.querySelector(`[data-mtp-id="${rt.id("maybe")}"]`)!.getAttribute("marker-end")).toBeNull();
    void svg;
  });
});
