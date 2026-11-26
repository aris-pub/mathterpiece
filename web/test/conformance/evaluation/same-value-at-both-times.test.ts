// Conformance tests of the rule same-value-at-both-times (docs/spec/evaluation.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";
import { live } from "../compile.ts";
import { bothTimes, bothTimesMany, real } from "./shared.ts";

const X = fc.double({ min: -100, max: 100, noNaN: true });
const CONSTANT = fc.double({ min: -1000, max: 1000, noNaN: true }).map(real);
// A divisor that is never 0, since a division by a known 0 is a compile error.
const DIVISOR = fc.constantFrom("3.0", "0.1", "-7.5", "1e-3", "1e10");

// An expression of X. It leaves out the functions on reals, such as sin and exp, that may differ at
// the two times today (mtp-ydd4.7.38), and sums of more than two reals, which are tested below.
const { expr: EXPRESSION } = fc.letrec<{ expr: string }>((tie) => ({
  expr: fc.oneof(
    { maxDepth: 3, depthSize: "small" },
    fc.constant("X"),
    CONSTANT,
    fc.tuple(tie("expr"), tie("expr")).map(([a, b]) => `(+ ${a} ${b})`),
    fc
      .tuple(fc.constantFrom("-", "*"), fc.array(tie("expr"), { minLength: 2, maxLength: 3 }))
      .map(([op, args]) => `(${op} ${args.join(" ")})`),
    fc.tuple(tie("expr"), DIVISOR).map(([a, d]) => `(/ ${a} ${d})`),
    tie("expr").map((a) => `(sqrt (abs ${a}))`),
    tie("expr").map((a) => `(abs ${a})`),
    tie("expr").map((a) => `(round ${a})`),
  ),
}));

describe("rule same-value-at-both-times: folded and drawn values are the same", () => {
  const cases: [string, (x: string) => string, string, string?][] = [
    ["+", (x) => `(+ ${x} 0.1)`, "0.2"],
    ["*", (x) => `(* ${x} 3)`, "0.1"],
    ["/", (x) => `(/ 1 ${x})`, "3", "real|none"],
    ["sqrt", (x) => `(sqrt ${x})`, "2", "real|none"],
    ["sin", (x) => `(sin ${x})`, "0.5"],
    ["round", (x) => `(round ${x})`, "2.5", "int"],
    ["format", (x) => `f'{${x}:.2f}'`, "0.125", "string"],
  ];
  for (const [what, expr, x, type] of cases) {
    it(what, () => {
      const [folded, drawn] = bothTimes(expr, x, type);
      expect(drawn).toEqual(folded);
    });
  }

  // Each run compiles one source that holds every case of the run.
  it("a generated expression of +, -, *, /, sqrt, abs and round", () => {
    fc.assert(
      fc.property(fc.array(fc.tuple(EXPRESSION, X), { minLength: 1, maxLength: 12 }), (cases) =>
        bothTimesMany(cases).every(([folded, drawn]) => folded === drawn),
      ),
      { numRuns: 8 },
    );
  });

  it.fails(
    "a sum of three reals (no bead: the compiler adds with Python's sum, which makes up for rounding errors, and the runtime adds from left to right, so (+ 0.3 0.1 0.2) is 0.6 when folded and 0.6000000000000001 while drawing)",
    () => {
      const sums = fc
        .tuple(fc.constantFrom("(+ X A B)", "(sum {X A B})"), X, CONSTANT, CONSTANT)
        .map(([form, x, a, b]): [string, number] => [form.replace("A", a).replace("B", b), x]);
      fc.assert(
        fc.property(fc.array(sums, { minLength: 1, maxLength: 12 }), (cases) =>
          bothTimesMany(cases).every(([folded, drawn]) => folded === drawn),
        ),
        { numRuns: 8, examples: [[[["(+ X 0.1 0.2)", 0.3]]]], endOnFailure: true },
      );
    },
  );

  it("a generated number with a format spec", () => {
    const cases = fc.array(
      fc.tuple(
        fc.integer({ min: 0, max: 6 }).map((places) => `f'{X:.${places}f}'`),
        fc.double({ min: -1e6, max: 1e6, noNaN: true }),
      ),
      { minLength: 1, maxLength: 12 },
    );
    fc.assert(
      fc.property(cases, (cases) => bothTimesMany(cases, "string").every(([folded, drawn]) => folded === drawn)),
      { numRuns: 8 },
    );
  });

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

describe("rule same-value-at-both-times: a result past the limit", () => {
  const cases: [string, (x: string) => string, number][] = [
    ["a product of three", (x) => `(* ${x} ${x} ${x})`, 1e150],
    ["a product past the largest binary64 number", (x) => `(* ${x} ${x} ${x} 1e-310)`, 1e150],
    ["a power", (x) => `(^ ${x} 3.5)`, 1e100],
    ["exp", (x) => `(exp ${x})`, 1000],
    ["dist", (x) => `(dist [${x} 0] [(- ${x}) 0])`, 1e150],
  ];
  for (const [what, expr, x] of cases) {
    it(what, () => {
      const [rt, v] = live(`(real x 1 (>= 0)) (real folded ${expr(String(x))}) (real drawn ${expr("x")})`);
      rt.write(rt.id("x"), null, x);
      expect(v("drawn")).toBe(v("folded"));
    });
  }
});
