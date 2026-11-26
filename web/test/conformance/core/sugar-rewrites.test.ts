// Conformance tests of the rule sugar-rewrites (docs/spec/core.md).
import { describe, expect, it } from "vitest";
import { drag, SHAPE } from "./shared.ts";

describe("rule sugar-rewrites: a drag written with a name means its move", () => {
  const cases: [string, string, string][] = [
    ["pos", "on-drag p p.pos", "on-drag p (move p.pos (to pointer))"],
    ["x", "on-drag p p.x", "on-drag p (move p.x (to (. pointer 0)))"],
    ["y", "on-drag p p.y", "on-drag p (move p.y (to (. pointer 1)))"],
  ];
  for (const [what, short, long] of cases) {
    it(`a drag of ${what}`, () => {
      const a = drag(`${SHAPE}(canvas v s (${short}))`, "p", [1.5, 1], [3, 4]);
      const b = drag(`${SHAPE}(canvas v s (${long}))`, "p", [1.5, 1], [3, 4]);
      expect(a("p", "pos")).toEqual(b("p", "pos"));
    });
  }
});
