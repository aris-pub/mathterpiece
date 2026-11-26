// Conformance tests of the rule equality-by-content (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";
import { live } from "../compile.ts";

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
