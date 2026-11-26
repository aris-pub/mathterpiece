// Conformance tests of the rule rounding (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";
import { decimalPlaces, rounded } from "./shared.ts";

const WRITES = fc.oneof(
  fc.double({ min: -2e6, max: 2e6, noNaN: true }),
  fc.integer({ min: -1e6, max: 1e6 }).map((n) => n + 0.5),
  fc.integer({ min: -1e8, max: 1e8 }).map((n) => n / 100),
);

describe("rule rounding: halves round away from zero while drawing", () => {
  it("a write into an int", () => {
    const [rt, v] = live(`(int n 0 (>= -1000000) (<= 1000000))`);
    fc.assert(
      fc.property(WRITES, (x) => {
        rt.write(rt.id("n"), null, x);
        return v("n") === Number(rounded(Math.max(-1e6, Math.min(1e6, x)), 0));
      }),
      { numRuns: 1000, examples: [[2.5], [-2.5]] },
    );
  });

  it("a write into an int is clamped, then rounded", () => {
    const [rt, v] = live(`(int n 0 (>= 0) (<= 10))`);
    rt.write(rt.id("n"), null, 10.4);
    expect(v("n")).toBe(10);
  });

  // Whether a zero keeps its sign is not part of this rule, so a result of zero is left out.
  it("a format spec, on the shortest decimal form", () => {
    const places = [0, 1, 2, 3, 4, 5, 6];
    const [rt, v] = live(
      `(real x 0 (>= -1e6) (<= 1e6)) ${places.map((p) => `(string s${p} f'{x:.${p}f}')`).join(" ")}`,
    );
    fc.assert(
      fc.property(WRITES.filter((x) => Math.abs(x) <= 1e6), fc.constantFrom(...places), (x, p) => {
        fc.pre(p <= decimalPlaces(x) && Number(rounded(x, p)) !== 0);
        rt.write(rt.id("x"), null, x);
        return v(`s${p}`) === rounded(x, p);
      }),
      { numRuns: 1000, examples: [[0.125, 2], [2.675, 2]] },
    );
  });

  it.fails(
    "a format spec with more places than the shortest decimal form (no bead: the runtime shows the digits of the binary value, so 0.1 to 17 places is 0.10000000000000001)",
    () => {
      const [rt, v] = live(`(real x 0 (>= -1e6) (<= 1e6)) (string s f'{x:.17f}')`);
      fc.assert(
        fc.property(fc.double({ min: -1e6, max: 1e6, noNaN: true }), (x) => {
          fc.pre(Number(rounded(x, 17)) !== 0);
          rt.write(rt.id("x"), null, x);
          return v("s") === rounded(x, 17);
        }),
        { numRuns: 200, examples: [[0.1]], endOnFailure: true },
      );
    },
  );
});
