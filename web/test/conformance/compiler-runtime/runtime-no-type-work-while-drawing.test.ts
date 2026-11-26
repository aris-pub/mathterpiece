// Conformance tests of the rule runtime-no-type-work-while-drawing (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule runtime-no-type-work-while-drawing: a write is brought into its constraints", () => {
  it("clamped", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 3))`);
    rt.write(rt.id("n"), null, 5);
    expect(v("n")).toBe(3);
  });

  it("rounded into an int", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 3))`);
    rt.write(rt.id("n"), null, 1.6);
    expect(v("n")).toBe(2);
  });

  it("wrapped", () => {
    const [rt, v] = live(`(real a 0 (wrap 0 360))`);
    rt.write(rt.id("a"), null, 370);
    expect(v("a")).toBeCloseTo(10, 9);
  });
});
