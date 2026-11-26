// Conformance tests of the rule matching (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";

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
