// Conformance tests of the rule operations-that-give-none (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule operations-that-give-none: an operation while drawing", () => {
  it("division by zero gives none", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1)) (real|none q (/ 1 x))`);
    rt.write(rt.id("x"), null, 0);
    expect(v("q")).toBe(null);
  });

  const poles: [string, string, number][] = [
    ["tand at 90 degrees", "(tand k)", 90],
    ["secd at 270 degrees", "(secd k)", 270],
    ["cotd at 180 degrees", "(cotd k)", 180],
    ["csc at 0", "(csc k)", 0],
    ["log at 0", "(log k)", 0],
    ["a base of 1", "(log 2 k)", 1],
    ["sqrt below 0", "(sqrt k)", -1],
    ["asin above 1", "(asin k)", 2],
    ["0 to a negative power", "(^ k -1)", 0],
  ];
  for (const [what, expr, k] of poles) {
    it(`${what} gives none`, () => {
      const [rt, v] = live(`(real k 1 (>= -1e6) (<= 1e6)) (real|none t ${expr})`);
      rt.write(rt.id("k"), null, k);
      expect(v("t")).toBe(null);
    });
  }

  it("a result past the largest binary64 number is not none", () => {
    const [rt, v] = live(`(real k 1) (real|none t (* k k k))`);
    rt.write(rt.id("k"), null, 1e150);
    expect(v("t")).toBe(1e150);
  });

  it("a position outside the list gives none", () => {
    const [rt, v] = live(`(int i 0 (>= 0) (<= 5)) (int|none q (. {1 2 3} i))`);
    rt.write(rt.id("i"), null, 3);
    expect(v("q")).toBe(null);
    rt.write(rt.id("i"), null, 2);
    expect(v("q")).toBe(3);
  });
});
