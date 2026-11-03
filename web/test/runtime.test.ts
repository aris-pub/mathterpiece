// The live model on .mtpc files the compiler writes (built by `just web-examples` from
// test/fixtures/runtime/*.mtp).
import { describe, expect, it } from "vitest";
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
