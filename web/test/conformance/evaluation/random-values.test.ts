// Conformance tests of the rule random-values (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";
import { hash, u, RANDOM_FREE, randomLive } from "./shared.ts";

const SEEDS = fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER });
const LISTS = fc.array(fc.integer({ min: -100, max: 100 }), { minLength: 1, maxLength: 8 });

/** The live model of RANDOM_FREE, and a writer of its variables by name. */
function model() {
  const m = randomLive(RANDOM_FREE);
  return { ...m, write: (name: string, x: unknown) => m.rt.write(m.rt.id(name), null, x) };
}

describe("rule random-values: each random function from the seed and its site", () => {
  it("rand from lo to hi", () => {
    const { v, site, write } = model();
    const bounds = fc
      .tuple(fc.double({ min: -1e6, max: 1e6, noNaN: true }), fc.double({ min: 0, max: 1e6, noNaN: true }))
      .map(([lo, width]) => [lo, lo + width] as const);
    fc.assert(
      fc.property(SEEDS, bounds, (s, [lo, hi]) => {
        write("s", s);
        write("lo", lo);
        write("hi", hi);
        return v("b") === lo + u(s, site("b"), 0) * (hi - lo);
      }),
      { numRuns: 1000, examples: [[7, [2, 5]]] },
    );
  });

  it("rand-int from lo to hi, both included", () => {
    const { v, site, write } = model();
    const bounds = fc
      .tuple(fc.integer({ min: -1e6, max: 1e6 }), fc.integer({ min: 0, max: 1e6 }))
      .map(([lo, width]) => [lo, lo + width] as const);
    fc.assert(
      fc.property(SEEDS, bounds, (s, [lo, hi]) => {
        write("s", s);
        write("ilo", lo);
        write("ihi", hi);
        return v("c") === lo + Math.floor(u(s, site("c"), 0) * (hi - lo + 1));
      }),
      { numRuns: 1000, examples: [[7, [1, 6]]] },
    );
  });

  it("pick", () => {
    const { v, site, write } = model();
    fc.assert(
      fc.property(SEEDS, LISTS, (s, xs) => {
        write("s", s);
        write("xs", xs);
        return v("d") === xs[Math.floor(u(s, site("d"), 0) * xs.length)];
      }),
      { numRuns: 1000, examples: [[7, [10, 20, 30]]] },
    );
  });

  it("shuffle", () => {
    const { v, site, write } = model();
    fc.assert(
      fc.property(SEEDS, LISTS, (s, xs) => {
        write("s", s);
        write("xs", xs);
        const out = [...xs];
        for (let i = out.length - 1; i > 0; i--) {
          const j = Math.floor(u(s, site("e"), i) * (i + 1));
          [out[i], out[j]] = [out[j]!, out[i]!];
        }
        expect(v("e")).toEqual(out);
      }),
      { numRuns: 1000, examples: [[7, [1, 2, 3, 4]]] },
    );
  });

  it("a roll of the dice writes next-seed", () => {
    const [rt, v] = live(`(import rand rand) (rand-seed s 7) (real a (rand))`);
    rt.write(rt.id("s"), null, hash(7, 0x9e3779b9));
    expect(v("a")).toBe(u(hash(7, 0x9e3779b9), 0, 0));
  });

  it.fails("rand-int with lo above hi gives none (mtp-y7vp: rand and rand-int do not check lo and hi)", () => {
    const [rt, v] = live(`(import rand rand-int) (rand-seed s 7) (int lo 1 (>= 0) (<= 10)) (int|none c (rand-int lo 3))`);
    rt.write(rt.id("lo"), null, 10);
    expect(v("c")).toBe(null);
  });
});
