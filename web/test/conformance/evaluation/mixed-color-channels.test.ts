// Conformance tests of the rule mixed-color-channels (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";

describe("rule mixed-color-channels: a channel that lies halfway rounds up while drawing", () => {
  it("rounds 2.5 up", () => {
    const [rt, v] = live(`(real t 0 (>= 0) (<= 1)) (color a (mix #'#000000' #'#050505' t))`);
    rt.write(rt.id("t"), null, 0.5);
    expect(v("a")).toBe("#030303ff");
  });
});
