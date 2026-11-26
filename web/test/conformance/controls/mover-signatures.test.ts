// Conformance tests of the rule mover-signatures (docs/spec/controls.md). The movers keep the
// form of today's .mtpc: each names the animation that is its effect.
import { describe, expect, it } from "vitest";
import { schemaProblem } from "../../../src/schema.ts";
import { REAL_0_1, control, input, mtpc, num, page, pass, str, valueOf, variable } from "./shared.ts";

const transition = { kind: "transition", type: "transition", access: "scene", name: null, from: num(0), to: num(1), duration: 1, ease: null, path: null };
const animation = { kind: "animation", type: "animation", access: "scene", name: null, steps: ["move", [0, null], 1, 1, "linear"] };

describe("rule mover-signatures: a mover takes a movement, its effect, which is required", () => {
  it("a press of a button plays its effect from the start", () => {
    const button = control("button", "go", { animation: 2, attrs: { label: str("go") } });
    const model = page(`<mtp-button model="m" name="go"></mtp-button>`, mtpc(variable("k", REAL_0_1, 0), transition, animation, button));
    input("mtp-button", "button").click();
    pass(0.5);
    expect(valueOf(model, "k")).toBeGreaterThan(0.3);
    input("mtp-button", "button").click();
    expect(valueOf(model, "k")).toBe(0);
    pass(1);
    expect(valueOf(model, "k")).toBe(1);
  });

  it("a button, a play and a stepper with no effect do not match the schema", () => {
    for (const kind of ["button", "play", "stepper"]) {
      const mover = control(kind, "go", { attrs: { label: str("go") } });
      expect(schemaProblem(mtpc(variable("k", REAL_0_1, 0), transition, animation, mover))).not.toBe(null);
    }
  });
});
