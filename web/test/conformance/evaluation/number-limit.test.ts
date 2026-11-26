// Conformance tests of the rule number-limit (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";
import { clamp } from "./shared.ts";

const NUMBERS = fc.double({ noNaN: true, noDefaultInfinity: true });

describe("rule number-limit: a write beyond the limit is clamped to it", () => {
  it("a number", () => {
    const [rt, v] = live(`(real k 0)`);
    fc.assert(
      fc.property(NUMBERS, (x) => {
        rt.write(rt.id("k"), null, x);
        return v("k") === clamp(x);
      }),
      { numRuns: 1000, examples: [[1e200]] },
    );
  });

  it.fails("each number of a point (mtp-ydd4.7.18: constrain clamps only a single number, so [1.0000000000000002e150 0] stays as written)", () => {
    const [rt, v] = live(`(point p [0 0])`);
    fc.assert(
      fc.property(NUMBERS, NUMBERS, (x, y) => {
        rt.write(rt.id("p"), null, [x, y]);
        expect(v("p")).toEqual([clamp(x), clamp(y)]);
      }),
      { numRuns: 1000, examples: [[1.0000000000000002e150, 0], [1e200, 0]], endOnFailure: true },
    );
  });
});

describe("rule number-limit: a product of two reals is rounded, then clamped", () => {
  it("a generated product", () => {
    const [rt, v] = live(`(real k 1) (real t (* k k))`);
    fc.assert(
      fc.property(NUMBERS, (x) => {
        rt.write(rt.id("k"), null, x);
        return v("t") === clamp(clamp(x) * clamp(x));
      }),
      { numRuns: 1000 },
    );
  });
});

describe("rule number-limit: a result is clamped to the limit", () => {
  it("a product", () => {
    const [rt, v] = live(`(real k 1 (>= 0) (<= 1e150)) (real t (* k k k))`);
    rt.write(rt.id("k"), null, 1e150);
    expect(v("t")).toBe(1e150);
  });

  it("a sum", () => {
    // Each item is clamped to 1e150 at k = 1e150, and so is their sum.
    const [rt, v] = live(`(real k 1 (>= 0) (<= 1e150)) (real t (sum {(* k k) (* k k)}))`);
    rt.write(rt.id("k"), null, 1e150);
    expect(v("t")).toBe(1e150);
  });

  it("an operation with several arguments is clamped once", () => {
    const [rt, v] = live(`(real k 1) (real t (+ k k (- k)))`);
    rt.write(rt.id("k"), null, 1e150);
    expect(v("t")).toBe(1e150);
  });

  const cases: [string, string, number, number][] = [
    ["a quotient", "(/ 1 k)", 1e-200, 1e150],
    ["a power", "(^ k 400)", -10, 1e150],
    ["a negative power", "(^ k 401)", -10, -1e150],
    ["exp", "(exp k)", 1000, 1e150],
    ["rad", "(rad k)", -1e150, -1e150],
    ["csc", "(csc k)", 1e-300, 1e150],
    ["lerp", "(lerp 0 k k)", 1e150, 1e150],
  ];
  for (const [what, expr, k, limit] of cases) {
    it(what, () => {
      const [rt, v] = live(`(real k 1) (real|none t ${expr})`);
      rt.write(rt.id("k"), null, k);
      expect(v("t")).toBe(limit);
    });
  }

  it("each part of a complex", () => {
    const [rt, v] = live(`(real k 1) (complex t (* (+ k (* k 1i)) k))`);
    rt.write(rt.id("k"), null, 1e100);
    const t = v("t") as { re: number; im: number };
    expect([t.re, t.im]).toEqual([1e150, 1e150]);
  });

  it("each number of a point", () => {
    const [rt, v] = live(`(real k 1) (point t (* [k (- k)] k))`);
    rt.write(rt.id("k"), null, 1e100);
    expect(v("t")).toEqual([1e150, -1e150]);
  });
});
