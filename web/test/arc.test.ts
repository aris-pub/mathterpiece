// Arcs and rings (mtp-5zmn; docs/reference.md, "The scene and shapes").
import { describe, expect, it } from "vitest";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

const close = (xs: number[]) => xs.map((x) => Math.round(x * 1e9) / 1e9);

function drawn() {
  const rt = load("arc");
  const svg = draw(rt, rt.id("v"));
  const el = (n: string) => svg.querySelector(`[data-mtp-id="${rt.id(n)}"]`) as SVGElement;
  return { rt, svg, el, d: (n: string) => el(n).getAttribute("d") };
}

describe("arcs", () => {
  it("draw as a path from one angle to the other, counterclockwise", () => {
    const { el, d } = drawn();
    expect(el("quarter").tagName).toBe("path");
    expect(d("quarter")).toBe("M2,0A2,2,0,0,1,0,2");
  });

  it("run clockwise when the second angle is smaller", () => {
    expect(drawn().d("back")).toBe("M0,2A2,2,0,0,0,2,0");
  });

  it("are whole with no angles, drawn in two halves", () => {
    expect(drawn().d("whole")).toBe("M2,0A2,2,0,0,1,-2,0A2,2,0,0,1,2,0");
  });

  it("go at most one turn", () => {
    expect(drawn().d("over")).toBe(drawn().d("whole"));
  });

  it("draw nothing when the angles are equal", () => {
    expect(drawn().d("none-at-all")).toBe("");
  });

  it("follow their angles", () => {
    const { rt } = drawn();
    rt.write(rt.id("t"), null, 180);
    const svg = draw(rt, rt.id("v"));
    expect(svg.querySelector(`[data-mtp-id="${rt.id("moving")}"]`)!.getAttribute("d")).toBe("M3,1A2,2,0,0,1,-1,1");
  });

  it("are never filled", () => {
    expect(drawn().el("quarter").style.getPropertyValue("fill")).toBe("none");
  });

  it("have their center as their position", () => {
    const { rt } = drawn();
    expect(rt.value(rt.id("moving"), "pos")).toEqual([1, 1]);
  });

  it("have the box around the arc itself", () => {
    const { rt } = drawn();
    expect(close(rt.box(rt.id("quarter"), null)!)).toEqual([0, 0, 2, 2]);
    expect(close(rt.box(rt.id("slanted"), null)!)).toEqual(close([-Math.SQRT2, Math.SQRT2, Math.SQRT2, 2]));
    expect(close(rt.box(rt.id("whole"), null)!)).toEqual([-2, -2, 2, 2]);
  });
});

describe("rings", () => {
  it("draw the region between the two circles", () => {
    const { el, d } = drawn();
    expect(d("band")).toBe("M2,0A2,2,0,0,1,0,2L0,1A1,1,0,0,0,1,0Z");
    expect(el("band").style.getPropertyValue("fill")).toBe("#ff0000ff");
  });

  it("are a pie slice when the width is the radius", () => {
    expect(drawn().d("pie")).toBe("M2,0A2,2,0,0,1,0,2L0,0Z");
  });

  it("stop at the center when the width is larger than the radius", () => {
    expect(drawn().d("too-wide")).toBe(drawn().d("pie"));
  });

  it("are whole with no angles: two circles, the inner one run the other way", () => {
    expect(drawn().d("annulus")).toBe(
      "M2,0A2,2,0,0,1,-2,0A2,2,0,0,1,2,0ZM1,0A1,1,0,0,0,-1,0A1,1,0,0,0,1,0Z",
    );
  });

  it("have the box around both edges", () => {
    const { rt } = drawn();
    expect(close(rt.box(rt.id("band"), null)!)).toEqual([0, 0, 2, 2]);
    expect(close(rt.box(rt.id("thin"), null)!)).toEqual(close([0.5, 0.5, Math.sqrt(3), Math.sqrt(3)]));
    expect(close(rt.box(rt.id("annulus"), null)!)).toEqual([-2, -2, 2, 2]);
  });

  it("clip a container", () => {
    const { rt, svg } = drawn();
    expect(svg.querySelector("clipPath")!.firstElementChild!.tagName).toBe("path");
    expect(close(rt.box(rt.id("g"), null)!)).toEqual([-3, -3, 3, 3]);
  });
});
