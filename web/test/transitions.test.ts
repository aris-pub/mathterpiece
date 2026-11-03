// How a move's value follows its ease (docs/reference.md, "Transitions and animations").
import { describe, expect, it } from "vitest";
import { along } from "../src/transitions.ts";

describe("along", () => {
  it("goes past the end when the ease goes past 1, for numbers and points", () => {
    // An ease that overshoots, such as a spring, must show its overshoot.
    expect(along(5, 0, 1.2, "number")).toBeCloseTo(-1);
    expect(along([0, 0], [2, 4], 1.5, "point")).toEqual([3, 6]);
    expect(along(0, 10, -0.1, "number")).toBeCloseTo(-1);
  });

  it("ends exactly at the end at 1", () => {
    expect(along(0.1, 0.3, 1, "number")).toBe(0.3);
    expect(along([0.1, 0.2], [0.3, 0.7], 1, "point")).toEqual([0.3, 0.7]);
  });

  it("stops a color and a jump at the end", () => {
    expect(along("#000000ff", "#ffffffff", 1.4, "color")).toBe("#ffffffff");
    expect(along("a", "b", 1.4, "jump")).toBe("b");
  });
});
