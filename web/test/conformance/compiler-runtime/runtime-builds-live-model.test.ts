// Conformance tests of the rule runtime-builds-live-model (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule runtime-builds-live-model: the live model is built once, then kept current", () => {
  it("gives every free variable its starting value", () => {
    const [, v] = live(`(real k 3) (point p [1 2])`);
    expect([v("k"), v("p")]).toEqual([3, [1, 2]]);
  });

  it("reads a free starting value once", () => {
    const [rt, v] = live(`(real a 1 (>= 0) (<= 10)) (real k free@(* 2 a))`);
    expect(v("k")).toBe(2);
    rt.write(rt.id("a"), null, 5);
    expect(v("k")).toBe(2);
  });

  it("computes again only what depends on what changed", () => {
    const [rt, v] = live(`(real a 1) (real b 1) (real x (* 2 a)) (real y (* 3 b))`);
    expect([v("x"), v("y")]).toEqual([2, 3]);
    const before = rt.evaluations;
    rt.write(rt.id("a"), null, 2);
    expect([v("x"), v("y")]).toEqual([4, 3]);
    expect(rt.evaluations - before).toBe(1);
  });
});
