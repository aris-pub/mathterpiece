// A foreach over a count known only while drawing (docs/reference.md, "Special forms"): as many
// copies as the count can be at most, and copy k is there only while k is below the count.
import { describe, expect, it } from "vitest";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a foreach over a count that changes", () => {
  it("draws the first n copies", () => {
    const rt = load("bounded");
    const drawn = () => draw(rt, rt.id("v")).querySelectorAll("circle").length;
    expect(drawn()).toBe(3);
    rt.write(rt.id("n"), null, 5);
    expect(drawn()).toBe(5);
    rt.write(rt.id("n"), null, 0);
    expect(drawn()).toBe(0);
  });

  it("makes each copy from the one before", () => {
    const rt = load("bounded");
    expect([0, 1, 2].map((k) => rt.value(rt.id(`d${k}`), "x"))).toEqual([1, 2, 4]);
    expect(rt.value(rt.id("d4"), "x")).toBeNull();
  });
});
