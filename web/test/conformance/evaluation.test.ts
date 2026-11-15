// Conformance tests for docs/spec/evaluation.md: what only the runtime can show. A test that
// today's code fails, by a "Code differs" note of the spec, is written with it.fails and names the
// bead of the note.
import { describe, expect, it } from "vitest";
import { same } from "../../src/same.ts";
import { compile, live } from "./compile.ts";

/** The hash of the rule random-hash, written again from the rule. */
function hash(...xs: number[]): number {
  let h = 0x811c9dc5;
  for (const x of xs) {
    const word = ((x % 2 ** 32) + 2 ** 32) % 2 ** 32;
    h = Math.imul((h ^ word) >>> 0, 0x01000193) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
    h = Math.imul(h, 0x2c1b3c6d) >>> 0;
    h = (h ^ (h >>> 12)) >>> 0;
    h = Math.imul(h, 0x297a2d39) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
  }
  return h;
}

const u = (s: number, p: number, k: number) => hash(s, p, k) / 2 ** 32;

const RANDOM = `
(rand-seed s 7)
(real a (rand))
(real b (rand 2 5))
(int c (rand-int 1 6))
(real|none d (pick (as list[real] [10 20 30])))
(list[int] e (shuffle [1 2 3 4]))
`;

describe("rule random-hash: the hash of a seed, a site and a number", () => {
  it("gives rand the value u(s, p, 0)", () => {
    const [, v] = live(RANDOM);
    expect(v("a")).toBe(u(7, 0, 0));
  });

  it("uses each number modulo 2^32, so seeds equal modulo 2^32 draw the same values", () => {
    const [rt, v] = live(RANDOM);
    const before = [v("a"), v("b"), v("c"), v("e")];
    rt.write(rt.id("s"), null, 7 + 2 ** 32);
    expect([v("a"), v("b"), v("c"), v("e")]).toEqual(before);
  });
});

describe("rule random-values: each random function from the seed and its site", () => {
  it("rand from lo to hi", () => {
    const [, v] = live(RANDOM);
    expect(v("b")).toBe(2 + u(7, 1, 0) * (5 - 2));
  });

  it("rand-int from lo to hi, both included", () => {
    const [, v] = live(RANDOM);
    expect(v("c")).toBe(1 + Math.floor(u(7, 2, 0) * 6));
  });

  it("pick", () => {
    const [, v] = live(RANDOM);
    expect(v("d")).toBe([10, 20, 30][Math.floor(u(7, 3, 0) * 3)]);
  });

  it("shuffle", () => {
    const [, v] = live(RANDOM);
    const out = [1, 2, 3, 4];
    for (let i = 3; i > 0; i--) {
      const j = Math.floor(u(7, 4, i) * (i + 1));
      [out[i], out[j]] = [out[j]!, out[i]!];
    }
    expect(v("e")).toEqual(out);
  });

  it("a roll of the dice writes next-seed", () => {
    const [rt, v] = live(`(rand-seed s 7) (real a (rand))`);
    rt.write(rt.id("s"), null, hash(7, 0x9e3779b9));
    expect(v("a")).toBe(u(hash(7, 0x9e3779b9), 0, 0));
  });

  it.fails("rand-int with lo above hi gives none (mtp-y7vp: rand and rand-int do not check lo and hi)", () => {
    const [rt, v] = live(`(rand-seed s 7) (int lo 1 (>= 0) (<= 10)) (int|none c (rand-int lo 3))`);
    rt.write(rt.id("lo"), null, 10);
    expect(v("c")).toBe(null);
  });
});

describe("rule random-never-folded: a random value is known only while drawing", () => {
  it("is not written as a value in the .mtpc", () => {
    const doc = compile(RANDOM);
    const a = doc.objects[doc.names["a"]!]! as { value: { bound?: unknown } };
    expect(a.value.bound).toBeDefined();
  });
});

describe("rule matching: the tolerant comparison of the runtime", () => {
  it("reals match within 1e-12 or a millionth of the larger", () => {
    expect(same(1, 1 + 1e-13)).toBe(true);
    expect(same(0, 1e-13)).toBe(true);
    expect(same(1e9, 1e9 + 100)).toBe(true);
    expect(same(1, 1.001)).toBe(false);
  });

  it("points and lists match item by item, when their lengths are the same", () => {
    expect(same([1, 2], [1, 2 + 1e-13])).toBe(true);
    expect(same([1, 2], [1, 2, 3])).toBe(false);
  });

  it("bools, strings, colors and none match only exactly", () => {
    expect(same(true, true)).toBe(true);
    expect(same("a", "A")).toBe(false);
    expect(same("#000080ff", "#000080ff")).toBe(true);
    expect(same(null, null)).toBe(true);
    expect(same(null, 0)).toBe(false);
  });
});

/** The value folded by the compiler, and the value that the runtime computes from x. */
function bothTimes(expr: (x: string) => string, x: string, type = "real"): [unknown, unknown] {
  const [rt, v] = live(`(real x 0 (>= -1e6) (<= 1e6))
(${type} folded ${expr(x)})
(${type} drawn ${expr("x")})`);
  rt.write(rt.id("x"), null, Number(x));
  return [v("folded"), v("drawn")];
}

describe("rule same-value-at-both-times: folded and drawn values are the same", () => {
  const cases: [string, (x: string) => string, string, string?][] = [
    ["+", (x) => `(+ ${x} 0.1)`, "0.2"],
    ["*", (x) => `(* ${x} 3)`, "0.1"],
    ["/", (x) => `(/ 1 ${x})`, "3", "real|none"],
    ["sqrt", (x) => `(sqrt ${x})`, "2", "real|none"],
    ["sin", (x) => `(sin ${x})`, "0.5"],
    ["round", (x) => `(round ${x})`, "2.5", "int"],
    ["format", (x) => `$'{${x}:.2f}'`, "0.125", "string"],
  ];
  for (const [what, expr, x, type] of cases) {
    it(what, () => {
      const [folded, drawn] = bothTimes(expr, x, type);
      expect(drawn).toEqual(folded);
    });
  }

  it.fails("a ratio (mtp-ydd4.7.13: the runtime computes ratios as doubles)", () => {
    const [rt, v] = live(`(int n 2 (>= 0) (<= 10)) (bool a (= (+ (/ n 10) 1/5) 3/10))`);
    rt.write(rt.id("n"), null, 1);
    expect(v("a")).toBe(true);
  });

  it.fails("an int beyond 2^53 (mtp-ydd4.7.13: the runtime computes ints as doubles)", () => {
    const [rt, v] = live(`(int n 1 (>= 0) (<= 100)) (int a (+ (^ 2 n) 1))`);
    rt.write(rt.id("n"), null, 60);
    expect(BigInt(v("a") as number)).toBe(2n ** 60n + 1n);
  });

  it.fails("a mixed color (mtp-nk2w: the compiler rounds halves to even)", () => {
    const [rt, v] = live(`(real t 0 (>= 0) (<= 1))
(color folded (mix '#000000' '#050505' 0.5))
(color drawn (mix '#000000' '#050505' t))`);
    rt.write(rt.id("t"), null, 0.5);
    expect(v("drawn")).toEqual(v("folded"));
  });

  it.fails("mod of reals (mtp-ydd4.7.14: the runtime computes a - b * floor(a / b))", () => {
    const [folded, drawn] = bothTimes((x) => `(mod ${x} 0.1)`, "5.5");
    expect(drawn).toEqual(folded);
  });
});

describe("rule number-types: ints and ratios are exact while drawing", () => {
  it.fails("an int (mtp-ydd4.7.13: the runtime computes ints as doubles)", () => {
    const [, v] = live(`(int a (+ (^ 2 60) 1))`);
    expect(BigInt(v("a") as number)).toBe(2n ** 60n + 1n);
  });
});

describe("rule mixed-color-channels: a channel that lies halfway rounds up while drawing", () => {
  it("rounds 2.5 up", () => {
    const [rt, v] = live(`(real t 0 (>= 0) (<= 1)) (color a (mix '#000000' '#050505' t))`);
    rt.write(rt.id("t"), null, 0.5);
    expect(v("a")).toBe("#030303ff");
  });
});

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
    const [rt, v] = live(`(real x 0 (>= 0) (<= 10)) (string s $'{x:.2f}')`);
    rt.write(rt.id("x"), null, 0.125);
    expect(v("s")).toBe("0.13");
    rt.write(rt.id("x"), null, 2.675);
    expect(v("s")).toBe("2.68");
  });
});

describe("rule number-limit: a write beyond the limit is clamped to it", () => {
  it("a number", () => {
    const [rt, v] = live(`(real k 0)`);
    rt.write(rt.id("k"), null, 1e200);
    expect(v("k")).toBe(1e150);
  });

  it.fails("each number of a point (mtp-ydd4.7.18: constrain clamps only a single number)", () => {
    const [rt, v] = live(`(point p [0 0])`);
    rt.write(rt.id("p"), null, [1e200, 0]);
    expect(v("p")).toEqual([1e150, 0]);
  });

  it.fails("an overflow in sum gives none (mtp-ec05: sum does not catch the overflow)", () => {
    // Each item is 1e308 at k = 1e150, and their sum is beyond the largest real.
    const [rt, v] = live(`(real k 1 (>= 0) (<= 1e150)) (real|none t (sum [(* k k 1e8) (* k k 1e8)]))`);
    rt.write(rt.id("k"), null, 1e150);
    expect(v("t")).toBe(null);
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
    const [, v] = live(`(color ink 'navy') (bool same-color (= ink '#000080'))`);
    expect(v("same-color")).toBe(true);
  });
});

describe("rule operations-that-give-none: an operation while drawing", () => {
  it("division by zero gives none", () => {
    const [rt, v] = live(`(real x 1 (>= -1) (<= 1)) (real|none q (/ 1 x))`);
    rt.write(rt.id("x"), null, 0);
    expect(v("q")).toBe(null);
  });

  it("a position outside the list gives none", () => {
    const [rt, v] = live(`(int i 0 (>= 0) (<= 5)) (int|none q (. [1 2 3] i))`);
    rt.write(rt.id("i"), null, 3);
    expect(v("q")).toBe(null);
    rt.write(rt.id("i"), null, 2);
    expect(v("q")).toBe(3);
  });
});
