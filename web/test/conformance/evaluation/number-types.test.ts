// Conformance tests of the rule number-types (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule number-types: ints and ratios are exact while drawing", () => {
  it.fails("an int (mtp-ydd4.7.13: the runtime computes ints as doubles)", () => {
    const [, v] = live(`(int a (+ (^ 2 60) 1))`);
    expect(BigInt(v("a") as number)).toBe(2n ** 60n + 1n);
  });
});
