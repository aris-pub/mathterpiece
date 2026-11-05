// A fixed-size group (mtp-ggs): its members are measured in screen pixels around its position.
// Only the scale changes; whatever reads it sees one point, its position, with a box of no size,
// and a drag moves its translate.
import { describe, expect, it } from "vitest";
import { Drags } from "../src/drag.ts";
import { draw, zoom } from "../src/svg.ts";
import { load } from "./helpers.ts";

// Without a canvas on screen, a canvas is taken as 640 pixels wide: 20 units over 640 pixels.
const PIXEL = 20 / 640;

describe("a fixed-size group", () => {
  it("is where its translate puts it, for whatever reads it", () => {
    const rt = load("fixed-size");
    expect(rt.read(rt.id("follower"), "pos", null)).toEqual([1, 2]);
    rt.write(rt.id("grip"), "translate", [3, -1]);
    expect(rt.read(rt.id("follower"), "pos", null)).toEqual([3, -1]);
  });

  it("has a box of no size at its position, whatever its members", () => {
    const rt = load("fixed-size");
    expect(rt.box(rt.id("grip"), null)).toEqual([1, 2, 1, 2]);
    expect(rt.read(rt.id("beside"), "pos", null)).toEqual([1.5, 2.5]);
  });

  it("draws its members at one scene unit per screen pixel", () => {
    const rt = load("fixed-size");
    const svg = draw(rt, rt.id("v"));
    const g = svg.querySelector("g[data-mtp-fixed-size]")!;
    expect(g.getAttribute("transform")).toBe(`matrix(${PIXEL} 0 0 ${PIXEL} 1 2)`);
    // Its circle's radius is in pixels, and its text's size needs no converting.
    expect(g.querySelector("circle")!.getAttribute("r")).toBe("6");
    expect(g.querySelector("text")!.getAttribute("font-size")).toBe("16");
  });

  it("keeps its members' size on screen when the canvas zooms", () => {
    const rt = load("fixed-size");
    const svg = draw(rt, rt.id("v"));
    zoom(rt, rt.id("v"), svg, { scale: 2, dx: 0, dy: 0 });
    const g = svg.querySelector("g[data-mtp-fixed-size]")!;
    expect(g.getAttribute("transform")).toBe(`matrix(${PIXEL / 2} 0 0 ${PIXEL / 2} 1 2)`);
    expect(g.querySelector("text")!.getAttribute("font-size")).toBe("16");
  });

  it("is dragged by its translate, from a press on any member", () => {
    const rt = load("fixed-size");
    const drags = new Drags(rt);
    const tip = rt.id("tip");
    expect(drags.grab(tip, [1, 2])).toBe(true);
    expect(drags.targets).toEqual([`${rt.id("grip")}:translate`]);
    drags.move([4, 0]);
    expect(rt.value(rt.id("grip"), "translate")).toEqual([4, 0]);
    expect(rt.read(rt.id("follower"), "pos", null)).toEqual([4, 0]);
  });
});
