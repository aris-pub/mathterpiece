// The live model on .mtpc files the compiler writes (built by `just web-examples` from
// test/fixtures/runtime/*.mtp).
import { describe, expect, it } from "vitest";
import { BUILTINS } from "../src/builtins.ts";
import { load } from "./helpers.ts";

describe("recomputing only what changed", () => {
  it("computes a bound value once until something it reads is written", () => {
    const rt = load("chain");
    const [k, a] = [rt.id("k"), rt.id("a")];
    expect(rt.value(a)).toBe(2);
    const before = rt.evaluations;
    expect(rt.value(a)).toBe(2);
    expect(rt.evaluations).toBe(before);
    rt.write(k, null, 3);
    expect(rt.value(a)).toBe(6);
    expect(rt.evaluations).toBe(before + 1);
  });

  it("recomputes nothing that does not read what was written", () => {
    const rt = load("chain");
    for (const n of ["a", "b", "other"]) rt.value(rt.id(n));
    const before = rt.evaluations;
    rt.write(rt.id("j"), null, 5);
    for (const n of ["a", "b", "other"]) rt.value(rt.id(n));
    expect(rt.evaluations - before).toBe(1);
  });

  it("skips a write that changes nothing", () => {
    const rt = load("chain");
    expect(rt.write(rt.id("k"), null, 1)).toBe(false);
  });
});

describe("arithmetic on two numbers", () => {
  it("gives what the built-ins give, and none where they are undefined", () => {
    const rt = load("arith");
    const v = (name: string) => rt.value(rt.id(name));
    expect(v("over")).toBe(-1);
    expect(v("under")).toBe(-1);
    expect(v("div")).toBe(-1);
    expect(v("sum")).toBe(BUILTINS["+"]!(0.1, 0.2));
    expect(v("diff")).toBe(BUILTINS["-"]!(0.1, 0.2));
    expect(v("quot")).toBe(BUILTINS["/"]!(0.1, 0.2));
    expect([v("less"), v("same"), v("twice")]).toEqual([true, false, 14]);
    rt.write(rt.id("z"), null, 4);
    expect(v("div")).toBe(0.25);
    rt.write(rt.id("b"), null, 0.1);
    expect([v("less"), v("same"), v("diff")]).toEqual([false, true, 0]);
  });
});

describe("a function whose value follows only from its arguments", () => {
  it("is told apart from one that reads the model", () => {
    const rt = load("pure");
    // twice, fact (which calls itself) and first-x (a part of a list) follow from their
    // arguments; scaled reads k, and uses-scaled calls it.
    expect(rt.doc.functions.map((_, i) => rt.isPure(i))).toEqual([true, false, true, false, true]);
  });

  it("gives what it gave before for the same arguments, and one that reads the model follows its writes", () => {
    const rt = load("pure");
    const v = (name: string) => rt.value(rt.id(name));
    const all = () => ["a", "b", "e", "g", "h"].map(v);
    expect(all()).toEqual([2, 3, 120, 3, 1]);
    rt.write(rt.id("k"), null, 4);
    rt.write(rt.id("n"), null, 3);
    expect(all()).toEqual([8, 12, 6, 9, 4]);
    rt.write(rt.id("k"), null, 1);
    rt.write(rt.id("n"), null, 5);
    expect(all()).toEqual([2, 3, 120, 3, 1]);
    expect(rt.fn(4)([[[7, 1]]], null)).toBe(7);
    expect(rt.fn(4)([[]], null)).toBe(0);
  });
});

describe("writes", () => {
  it("clamp to a range, round an int and hold a choice", () => {
    const rt = load("writes");
    rt.write(rt.id("unit"), null, 2);
    expect(rt.value(rt.id("unit"))).toBe(1);
    rt.write(rt.id("n"), null, 2.5);
    expect(rt.value(rt.id("n"))).toBe(3);
    rt.write(rt.id("way"), null, "up");
    expect(rt.value(rt.id("way"))).toBe("left");
  });

  it("skip a write that breaks a strict bound", () => {
    const rt = load("writes");
    expect(rt.write(rt.id("pos"), null, 0)).toBe(false);
    expect(rt.value(rt.id("pos"))).toBe(1);
  });
});

describe("reads and frames", () => {
  it("converts a position through the transforms not shared with the reader", () => {
    const rt = load("frames");
    // q sits in g, so it reads p.x in g's frame; read from outside, g's translate counts.
    expect(rt.value(rt.id("q"), "x")).toBe(1);
    expect(rt.value(rt.id("outside"))).toBe(6);
    expect(rt.value(rt.id("inside"))).toBe(6);
  });

  it("gives a container's box again after a member or a transform on the way is written", () => {
    const rt = load("frames");
    const g = rt.id("g");
    const box = rt.box(g, null)!;
    rt.write(rt.id("p"), "x", 3);
    // q stands where p does, so both move.
    expect(rt.box(g, null)).toEqual([box[0]! + 2, box[1], box[2]! + 2, box[3]]);
    rt.write(g, "translate", [6, 0]);
    expect(rt.box(g, null)).toEqual([box[0]! + 3, box[1], box[2]! + 3, box[3]]);
  });

  it("converts again after a transform on the way is written", () => {
    const rt = load("frames");
    expect(rt.value(rt.id("outside"))).toBe(6);
    rt.write(rt.id("g"), "translate", [7, 0]);
    expect(rt.value(rt.id("outside"))).toBe(8);
    expect(rt.value(rt.id("inside"))).toBe(8);
    expect(rt.value(rt.id("q"), "x")).toBe(1);
  });
});

describe("none", () => {
  it("gives none where a function is undefined, and or? handles it", () => {
    const rt = load("none");
    expect(rt.value(rt.id("d"))).toBe(1);
    rt.write(rt.id("k"), null, 0);
    expect(rt.value(rt.id("d"))).toBe(0);
  });

  it("tells its listeners once for writes made together, with every change", () => {
    const rt = load("page");
    const seen: Set<string>[] = [];
    rt.onChange((changed) => seen.push(new Set(changed)));
    rt.together(() => {
      rt.write(rt.id("k"), null, 3);
      rt.write(rt.id("steps"), null, 2);
      rt.write(rt.id("k"), null, 4);
    });
    expect(seen).toHaveLength(1);
    // The written variables, and what is bound to them.
    for (const name of ["k", "steps"]) expect([...seen[0]!].some((c) => c === `${rt.id(name)}:`)).toBe(true);
    expect(rt.value(rt.id("k"))).toBe(4);
    rt.together(() => rt.write(rt.id("k"), null, 4));
    expect(seen).toHaveLength(1);
  });
});

describe("a list of two numbers where a point is expected (mtp-vrf9)", () => {
  it("is drawn as the point, and follows what it reads", () => {
    const rt = load("point-conversion");
    expect(rt.value(rt.id("from-let"), "pos")).toEqual([1, 3]);
    expect(rt.value(rt.id("from-func"), "pos")).toEqual([1, 2]);
    rt.write(rt.id("x"), null, 4);
    expect(rt.value(rt.id("from-let"), "pos")).toEqual([4, 3]);
    expect(rt.value(rt.id("from-func"), "pos")).toEqual([4, 2]);
  });
});
