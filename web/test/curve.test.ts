// Bézier curves (mtp-oya; docs/reference.md, "The scene and shapes").
import { describe, expect, it } from "vitest";
import { curveAt, curveBox } from "../src/curve.ts";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

const close = (xs: number[]) => xs.map((x) => Math.round(x * 1e9) / 1e9);

describe("curves", () => {
  it("draw as SVG paths, Q with one control and C with two", () => {
    const rt = load("curve");
    const svg = draw(rt, rt.id("v"));
    const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`) as SVGElement;
    expect(el("quad").tagName).toBe("path");
    expect(el("quad").getAttribute("d")).toBe("M0,0Q2,4 4,0");
    expect(el("cubic").getAttribute("d")).toBe("M0,0C0,3 4,3 4,0");
  });

  it("are never filled, and take heads", () => {
    const rt = load("curve");
    const svg = draw(rt, rt.id("v"));
    const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`) as SVGElement;
    expect(el("quad").style.getPropertyValue("fill")).toBe("none");
    expect(el("cubic").getAttribute("marker-end")).not.toBeNull();
    expect(el("quad").getAttribute("marker-end")).toBeNull();
  });

  it("have the mean of their ends and controls as their position", () => {
    const rt = load("curve");
    expect(close(rt.value(rt.id("quad"), "pos") as number[])).toEqual(close([2, 4 / 3]));
    expect(close(rt.value(rt.id("cubic"), "pos") as number[])).toEqual([2, 1.5]);
    rt.write(rt.id("k"), null, 5);
    expect(close(rt.value(rt.id("cubic"), "pos") as number[])).toEqual([2, 2.5]);
  });

  it("move their ends and controls together when their position is written", () => {
    const rt = load("curve");
    rt.write(rt.id("quad"), "pos", [12, 4 / 3]);
    expect(rt.value(rt.id("quad"), "from")).toEqual([10, 0]);
    expect(rt.value(rt.id("quad"), "to")).toEqual([14, 0]);
    expect(close((rt.value(rt.id("quad"), "controls") as number[][])[0]!)).toEqual([12, 4]);
    rt.write(rt.id("quad"), "x", 2);
    expect(rt.value(rt.id("quad"), "from")).toEqual([0, 0]);
  });

  it("have the smallest box around the curve, not around the controls", () => {
    // The quadratic peaks halfway, at 2, half its control's height.
    expect(close(curveBox([0, 0], [[2, 4]], [4, 0]))).toEqual([0, 0, 4, 2]);
    // The cubic peaks at three quarters of its controls' height.
    expect(close(curveBox([0, 0], [[0, 3], [4, 3]], [4, 0]))).toEqual([0, 0, 4, 2.25]);
    // A straight cubic has no turn.
    expect(close(curveBox([0, 0], [[1, 0], [3, 0]], [4, 0]))).toEqual([0, 0, 4, 0]);
    expect(close(curveAt([[0, 0], [2, 4], [4, 0]], 0.5))).toEqual([2, 2]);
  });

  it("are placed against by that box", () => {
    const rt = load("curve");
    expect(close(rt.value(rt.id("mark"), "pos") as number[])).toEqual([2, 2]);
  });
});
