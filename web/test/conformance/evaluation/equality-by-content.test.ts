// Conformance tests of the rule equality-by-content (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";
import { live } from "../compile.ts";

const REALS = fc.double({ min: -1e6, max: 1e6, noNaN: true });

describe("rule equality-by-content: numbers and lists compare by content while drawing", () => {
  // A second real that is often the first, its negative or the next binary64 number, since two
  // reals drawn on their own are almost never equal.
  const pairs = REALS.chain((a) =>
    fc.tuple(fc.constant(a), fc.oneof(fc.constant(a), fc.constant(-a), fc.constant(a + Number.EPSILON * Math.abs(a)), REALS)),
  );

  it("two reals are equal when they are the same number", () => {
    const [rt, v] = live(`(real a 0) (real b 0) (bool e (= a b)) (bool n (!= a b))`);
    fc.assert(
      fc.property(pairs, ([a, b]) => {
        rt.write(rt.id("a"), null, a);
        rt.write(rt.id("b"), null, b);
        return v("e") === (a === b) && v("n") === (a !== b);
      }),
      { numRuns: 1000, examples: [[[0, -0]]] },
    );
  });

  it("two lists are equal when they have the same length and their items are equal", () => {
    const [rt, v] = live(`(list[real] p {1}) (list[real] q {1}) (bool e (= p q))`);
    const list = fc.array(fc.integer({ min: 0, max: 2 }), { maxLength: 3 });
    fc.assert(
      fc.property(list, list, (p, q) => {
        rt.write(rt.id("p"), null, p);
        rt.write(rt.id("q"), null, q);
        return v("e") === (p.length === q.length && p.every((x, i) => x === q[i]));
      }),
      { numRuns: 1000 },
    );
  });
});

describe("rule equality-by-content: shapes compare by identity while drawing", () => {
  const scene = `(scene s (circle a (r 1)) (circle b (r 1)))`;

  it("two circles with the same attributes are not equal", () => {
    const [, v] = live(`${scene} (bool same-two (= a b))`);
    expect(v("same-two")).toBe(false);
  });

  it("a circle is equal to itself", () => {
    const [, v] = live(`${scene} (bool itself (= a a))`);
    expect(v("itself")).toBe(true);
  });

  it("a token by its value in the live model", () => {
    const [, v] = live(`(color ink #'navy') (bool same-color (= ink #'#000080'))`);
    expect(v("same-color")).toBe(true);
  });
});
