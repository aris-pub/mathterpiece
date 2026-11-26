// Conformance tests of the rule same-value-at-both-times (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";
import { live } from "../compile.ts";
import { bothTimes } from "./shared.ts";

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
