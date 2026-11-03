// Polylines and polygons (mtp-4nt; docs/reference.md, "The scene and shapes").
import { describe, expect, it } from "vitest";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

const close = (xs: number[]) => xs.map((x) => Math.round(x * 1e9) / 1e9);

describe("polylines and polygons", () => {
  it("draw as SVG polylines and polygons through their points", () => {
    const rt = load("polyline");
    const svg = draw(rt, rt.id("v"));
    const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`)!;
    expect(el("p").tagName).toBe("polyline");
    expect(el("p").getAttribute("points")).toBe("0,0 4,0 4,2");
    expect(el("q").tagName).toBe("polygon");
    expect(el("empty").getAttribute("points")).toBe("");
  });

  it("fill a polygon, never a polyline", () => {
    const rt = load("polyline");
    const svg = draw(rt, rt.id("v"));
    const fill = (n: string) => (svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`) as SVGElement).style.getPropertyValue("fill");
    expect(fill("p")).toBe("none");
    expect(fill("q")).toBe("#ff0000ff");
  });

  it("have the mean of their points as their position, [0 0] with none", () => {
    const rt = load("polyline");
    expect(close(rt.value(rt.id("q"), "pos") as number[])).toEqual(close([8 / 3, 2 / 3]));
    expect(rt.value(rt.id("empty"), "pos")).toEqual([0, 0]);
    expect(rt.value(rt.id("bendy"), "x")).toBe(0.5);
    rt.write(rt.id("k"), null, 3);
    expect(rt.value(rt.id("bendy"), "x")).toBe(1.5);
  });

  it("move every point when their position is written", () => {
    const rt = load("polyline");
    rt.write(rt.id("p"), "pos", [10, 10]);
    expect(close(rt.value(rt.id("p"), "pos") as number[])).toEqual([10, 10]);
    expect(close((rt.value(rt.id("p"), "points") as number[][])[0]!)).toEqual(close([22 / 3, 28 / 3]));
    rt.write(rt.id("q"), "x", 5);
    expect((rt.value(rt.id("q"), "points") as number[][]).map((pt) => close(pt))).toEqual(
      close([0, 4, 4].map((x) => x + 5 - 8 / 3)).map((x, k) => [x, [0, 0, 2][k]!]),
    );
  });

  it("have the box around their points, for placement", () => {
    const rt = load("polyline");
    expect(rt.box(rt.id("q"), null)).toEqual([0, 0, 4, 2]);
    expect(rt.value(rt.id("c"), "pos")).toEqual([4, 2]);
  });

  it("let a polygon clip a container", () => {
    const rt = load("polyline");
    const path = draw(rt, rt.id("v")).querySelector("clipPath")!;
    expect(path.firstElementChild!.tagName).toBe("polygon");
    expect(rt.box(rt.id("g"), null)).toEqual([0, 0, 2, 2]);
  });
});
