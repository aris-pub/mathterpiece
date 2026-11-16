// The runtime's built-ins on their own (docs/reference.md, "Functions"); each mirrors the
// compiler's folding in mathterpiece/builtins.py.
import { describe, expect, it } from "vitest";
import { BUILTINS, Complex, Undefined, frexp, ldexp, scaledProduct } from "../src/builtins.ts";

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

// The expected values are what Python's math.frexp and math.ldexp, and scaled_product in
// mathterpiece/builtins.py, give for the same inputs.
describe("the product past the largest binary64 number", () => {
  it("splits a number as frexp does", () => {
    const cases: [number, [number, number]][] = [
      [1, [0.5, 1]],
      [-1, [-0.5, 1]],
      [3, [0.75, 2]],
      [1e150, [0.6109872726999209, 499]],
      [5e-324, [0.5, -1073]],
      [2.2250738585072014e-308, [0.5, -1021]],
      [1e-310, [0.5752618031559393, -1029]],
      [1.7976931348623157e308, [0.9999999999999999, 1024]],
      [-7e-320, [-0.86474609375, -1060]],
    ];
    for (const [x, parts] of cases) expect(frexp(x)).toEqual(parts);
  });

  it("puts a number together again as ldexp does, rounding once", () => {
    const cases: [number, number, number][] = [
      [0.75, 1024, 1.348269851146737e308],
      [0.75, 1023, 6.741349255733685e307],
      [0.75, -1074, 5e-324],
      [0.75, -1073, 1e-323],
      [0.6, -1080, 0],
      [0.999, -1050, 8.280757e-317],
      [0.75, 2000, Infinity],
      [-0.9, -1060, -7.2855e-320],
    ];
    for (const [m, e, x] of cases) expect(ldexp(m, e)).toBe(x);
  });

  it("multiplies from left to right with the exponent kept apart", () => {
    expect(scaledProduct([1e150, 1e150, 1e150, 1e-310])).toBe(9.999999999999969e139);
    expect(scaledProduct([1e150, -1e150, 1e150, 1e-300, 3])).toBe(-2.9999999999999998e150);
    expect(scaledProduct([1e-200, 1e-200, 1e200, 1e200])).toBe(0.9999999999999998);
    expect(scaledProduct([0.1, 0.2, 0.3])).toBe(0.1 * 0.2 * 0.3);
    expect(scaledProduct([1e150, 1e150, 1e150, 0])).toBe(0);
    const c = scaledProduct([new Complex(1e150, 1e150), new Complex(1e150, -3e149), 1e150, new Complex(1e-300, 2e-301)]);
    expect(c).toEqual(new Complex(1.1599999999999999e150, 9.599999999999999e149));
  });

  it("clamps each part of a complex power", () => {
    expect(BUILTINS["^"]!(new Complex(1e150, 0), 3)).toEqual(new Complex(1e150, 0));
  });
});
