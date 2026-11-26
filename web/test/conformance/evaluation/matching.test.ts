// Conformance tests of the rule matching (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";

const REALS = fc.double({ min: -1e150, max: 1e150, noNaN: true });
// A second real near the first, so that both sides of each tolerance come up.
const NEAR = (a: number) =>
  fc.oneof(
    fc.constant(a),
    fc.double({ min: -1e-11, max: 1e-11, noNaN: true }).map((d) => a + d),
    fc.double({ min: -1e-5, max: 1e-5, noNaN: true }).map((f) => a * (1 + f)),
    REALS,
  );
const PAIRS = REALS.chain((a) => fc.tuple(fc.constant(a), NEAR(a)));

/** Whether two reals match by the rule: within 1e-12, or within a millionth of the larger size. */
const matchReals = (a: number, b: number) =>
  a === b || Math.abs(a - b) <= 1e-12 || Math.abs(a - b) <= 1e-6 * Math.max(Math.abs(a), Math.abs(b));

describe("rule matching: the tolerant comparison of the runtime", () => {
  it("reals match within 1e-12 or a millionth of the larger", () => {
    fc.assert(
      fc.property(PAIRS, ([a, b]) => same(a, b) === matchReals(a, b)),
      { numRuns: 2000, examples: [[[1, 1 + 1e-13]], [[0, 1e-13]], [[1e9, 1e9 + 100]], [[1, 1.001]]] },
    );
  });

  it("points and lists match item by item, when their lengths are the same", () => {
    const lists = fc.array(PAIRS, { maxLength: 4 }).chain((pairs) =>
      fc.tuple(
        fc.constant(pairs.map(([a]) => a)),
        fc.oneof(fc.constant(pairs.map(([, b]) => b)), fc.array(REALS, { maxLength: 4 })),
      ),
    );
    fc.assert(
      fc.property(lists, ([xs, ys]) => same(xs, ys) === (xs.length === ys.length && xs.every((x, i) => matchReals(x, ys[i]!)))),
      { numRuns: 2000, examples: [[[[1, 2], [1, 2 + 1e-13]]], [[[1, 2], [1, 2, 3]]]] },
    );
  });

  it("strings match only exactly", () => {
    const text = fc.string({ maxLength: 3, unit: fc.constantFrom("a", "A", " ", "b") });
    fc.assert(
      fc.property(text, text, (a, b) => same(a, b) === (a === b)),
      { numRuns: 1000, examples: [["a", "A"]] },
    );
  });

  it("bools, strings, colors and none match only exactly", () => {
    expect(same(true, true)).toBe(true);
    expect(same("a", "A")).toBe(false);
    expect(same("#000080ff", "#000080ff")).toBe(true);
    expect(same(null, null)).toBe(true);
    expect(same(null, 0)).toBe(false);
  });
});
