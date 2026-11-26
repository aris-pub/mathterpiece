// Conformance tests of the rule random-hash (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { u, RANDOM_FREE, randomLive } from "./shared.ts";

const SEEDS = fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER });

describe("rule random-hash: the hash of a seed, a site and a number", () => {
  it("gives rand the value u(s, p, 0)", () => {
    const { rt, v, site } = randomLive(RANDOM_FREE);
    fc.assert(
      fc.property(SEEDS, (s) => {
        rt.write(rt.id("s"), null, s);
        return v("a") === u(s, site("a"), 0);
      }),
      { numRuns: 1000, examples: [[7]] },
    );
  });

  it("uses each number modulo 2^32, so seeds equal modulo 2^32 draw the same values", () => {
    const { rt, v } = randomLive(RANDOM_FREE);
    const values = () => [v("a"), v("b"), v("c"), v("d"), v("e")];
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 2 ** 32 - 1 }), fc.integer({ min: 1, max: 2 ** 20 }), (s, k) => {
        rt.write(rt.id("s"), null, s);
        const before = values();
        rt.write(rt.id("s"), null, s + k * 2 ** 32);
        expect(values()).toEqual(before);
      }),
      { numRuns: 300, examples: [[7, 1]] },
    );
  });

  it.fails("a seed below 0 (mtp-ydd4.7.30: the type rand-seed is an int of at least 0, so a write of -1 gives 0)", () => {
    const { rt, v, site } = randomLive(RANDOM_FREE);
    fc.assert(
      fc.property(fc.integer({ min: -(2 ** 52), max: -1 }), (s) => {
        rt.write(rt.id("s"), null, s);
        return v("a") === u(s, site("a"), 0);
      }),
      { numRuns: 100, examples: [[-1]], endOnFailure: true },
    );
  });
});
