// The runtime's built-ins on their own (docs/reference.md, "Functions"); each mirrors the
// compiler's folding in mathterpiece/builtins.py.
import { describe, expect, it } from "vitest";
import { BUILTINS, Complex, Undefined } from "../src/builtins.ts";

const range = (start: number, stop: number, by: string, step: number) => BUILTINS.range!(start, stop, by, step) as number[];

describe("=", () => {
  const eq = BUILTINS["="]!;

  it("compares lists of points and numbers item by item", () => {
    expect(eq([[1, 2], [3, 4]], [[1, 2], [3, 4]])).toBe(true);
    expect(eq([[1, 2], [3, 4]], [[1, 2], [3, 5]])).toBe(false);
    expect(eq([[1, 2]], [[1, 2], [3, 4]])).toBe(false);
    expect(eq([1, 2, 3], [1, 2, 3])).toBe(true);
    expect(eq([0], [-0])).toBe(true);
    expect(eq([NaN], [NaN])).toBe(false);
  });

  it("compares long lists of points, again and again", () => {
    const trail = (shift: number) => Array.from({ length: 160 }, (_, i) => [i, i + shift]);
    const [a, b, c] = [trail(0), trail(0), trail(1)];
    for (let k = 0; k < 2; k++) {
      expect(eq(a, b)).toBe(true);
      expect(eq(a, c)).toBe(false);
      expect(eq(c, a)).toBe(false);
      expect(eq(a, a)).toBe(true);
    }
    const holes = Array.from({ length: 20 }, () => Number.NaN);
    expect(eq(holes, holes)).toBe(false);
  });

  it("compares none, colors and complex numbers inside a list", () => {
    expect(eq([null, 1], [null, 1])).toBe(true);
    expect(eq([null], [0])).toBe(false);
    expect(eq(["#ff0000ff"], ["#ff0000ff"])).toBe(true);
    expect(eq([new Complex(1, 0)], [1])).toBe(true);
    expect(eq([new Complex(1, 2)], [1])).toBe(false);
  });
});

describe("range (mtp-966)", () => {
  it("steps by a gap and leaves stop out", () => {
    expect(range(0, 5, "gap", 1)).toEqual([0, 1, 2, 3, 4]);
    expect(range(1, 2, "gap", 0.25)).toEqual([1, 1.25, 1.5, 1.75]);
    expect(range(5, 0, "gap", -2)).toEqual([5, 3, 1]);
  });

  it("gives no items for a gap that points away, or the same start and stop", () => {
    expect(range(0, 5, "gap", -1)).toEqual([]);
    expect(range(0, -5, "gap", 1)).toEqual([]);
    expect(range(3, 3, "gap", 1)).toEqual([]);
  });

  it("stops before stop with gaps that are not exact in binary", () => {
    expect(range(0, 0.3, "gap", 0.1)).toHaveLength(3);
    expect(range(0, 1, "gap", 0.1)).toHaveLength(10);
    expect(range(0, 1, "gap", 1 / 3)).toHaveLength(3);
  });

  it("computes each item from the start, so rounding does not add up", () => {
    expect(range(0, 100, "gap", 0.1)[999]).toBeCloseTo(99.9, 12);
  });

  it("gives num items from start to stop, both included", () => {
    expect(range(0, 1, "num", 5)).toEqual([0, 0.25, 0.5, 0.75, 1]);
    expect(range(1, 0, "num", 3)).toEqual([1, 0.5, 0]);
    expect(range(0, 0.3, "num", 4).at(-1)).toBe(0.3);
    expect(range(3, 7, "num", 1)).toEqual([3]);
    expect(range(3, 7, "num", 0)).toEqual([]);
    expect(range(3, 3, "num", 2)).toEqual([3, 3]);
  });

  it("is undefined for a gap of 0, a negative num, or more than a million items", () => {
    expect(() => range(0, 5, "gap", 0)).toThrow(Undefined);
    expect(() => range(0, 1, "num", -1)).toThrow(Undefined);
    expect(() => range(0, 1e9, "gap", 1)).toThrow(Undefined);
    expect(() => range(0, 1, "num", 2_000_000)).toThrow(Undefined);
  });
});

describe("sign (mtp-a5np)", () => {
  it("gives -1 below 0, 0 at 0 and 1 above 0", () => {
    // toEqual tells -0 from 0, so this also checks that -0 gives 0, as Python's fold does.
    expect([-3, -0.5, 0, -0, 2.5].map((x) => BUILTINS.sign!(x))).toEqual([-1, -1, 0, 0, 1]);
  });
});
