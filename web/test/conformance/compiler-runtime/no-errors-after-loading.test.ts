// Conformance tests of the rule no-errors-after-loading (docs/spec/compiler-runtime.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule no-errors-after-loading: nothing fails once the model is loaded", () => {
  it("an operation with no value gives none", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1)) (real|none q (/ 1 x))`);
    expect(() => rt.write(rt.id("x"), null, 0)).not.toThrow();
    expect(v("q")).toBe(null);
  });

  it("a write beyond a constraint is brought into it", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1))`);
    expect(() => rt.write(rt.id("x"), null, 5)).not.toThrow();
    expect(v("x")).toBe(1);
  });

  it.fails("a deep chain of calls (mtp-ydd4.7.15: a call too deep throws RangeError)", () => {
    const [rt, v] = live(`(int n 1 (>= 0) (<= 100000))
(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))
(int d (down n))`);
    rt.write(rt.id("n"), null, 100000);
    expect(() => v("d")).not.toThrow();
  });
});
