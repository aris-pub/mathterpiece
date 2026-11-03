// A container's clip (mtp-un2f; docs/reference.md, "Containers").
import { describe, expect, it } from "vitest";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("clipping a container", () => {
  it("draws the members inside a clip path made of the clip shape, in the container's frame", () => {
    const rt = load("clip");
    const svg = draw(rt, rt.id("v"));
    const g = svg.querySelector(`[data-mtp-id="${rt.id("g")}"]`)!;
    const ref = g.getAttribute("clip-path")!;
    const id = /^url\(#(.+)\)$/.exec(ref)![1]!;
    const path = svg.querySelector(`clipPath[id="${id}"]`)!;
    expect(path.parentElement).toBe(g);
    const rect = path.querySelector("rect")!;
    expect(["x", "y", "width", "height"].map((a) => rect.getAttribute(a))).toEqual(["-2", "-1", "4", "2"]);
  });

  it("never draws the clip shape itself", () => {
    const rt = load("clip");
    const svg = draw(rt, rt.id("v"));
    expect(svg.querySelectorAll(`[data-mtp-id="${rt.id("window")}"]`)).toHaveLength(0);
    expect(svg.querySelectorAll(`[data-mtp-id="${rt.id("a")}"]`)).toHaveLength(1);
  });

  it("gives each drawing its own clip path id", () => {
    const rt = load("clip");
    const ids = ["v", "w"].map((c) => draw(rt, rt.id(c)).querySelector("clipPath")!.id);
    expect(ids[0]).not.toBe(ids[1]);
  });

  it("cuts the container's box to the clip's, and follows the clip as it changes", () => {
    const rt = load("clip");
    expect(rt.box(rt.id("g"), null)).toEqual([-1, -1, 3, 1]);
    expect(rt.value(rt.id("under"), "pos")).toEqual([1, -1]);
    rt.write(rt.id("h"), null, 4);
    expect(rt.box(rt.id("g"), null)).toEqual([-1, -2, 3, 2]);
    expect(rt.value(rt.id("under"), "pos")).toEqual([1, -2]);
  });

  it("with the members wholly outside the clip, is an empty box at the clip's nearest edge", () => {
    const rt = load("clip");
    // Both circles move to x 24 in the scene, wholly right of the clip, which keeps -1 to 3.
    rt.write(rt.id("a"), "x", 23);
    rt.write(rt.id("b"), "x", 23);
    expect(rt.box(rt.id("g"), null)).toEqual([3, -1, 3, 1]);
  });
});
