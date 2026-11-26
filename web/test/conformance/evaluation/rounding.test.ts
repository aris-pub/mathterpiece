// Conformance tests of the rule rounding (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule rounding: halves round away from zero while drawing", () => {
  it("a write into an int", () => {
    const [rt, v] = live(`(int n 0 (>= -10) (<= 10))`);
    rt.write(rt.id("n"), null, 2.5);
    expect(v("n")).toBe(3);
    rt.write(rt.id("n"), null, -2.5);
    expect(v("n")).toBe(-3);
  });

  it("a write into an int is clamped, then rounded", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 10))`);
    rt.write(rt.id("n"), null, 10.4);
    expect(v("n")).toBe(10);
  });

  it("a format spec, on the shortest decimal form", () => {
    const [rt, v] = live(`(real x 0 (>= 0) (<= 10)) (string s f'{x:.2f}')`);
    rt.write(rt.id("x"), null, 0.125);
    expect(v("s")).toBe("0.13");
    rt.write(rt.id("x"), null, 2.675);
    expect(v("s")).toBe("2.68");
  });
});
