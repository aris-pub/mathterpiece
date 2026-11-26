// Conformance tests of the rule jumpers-and-movers (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import { REAL_0_1, control, input, mtpc, none, num, page, pass, place, press, str, valueOf, variable } from "./shared.ts";

describe("rule jumpers-and-movers: a jumper writes its target by a jump, a mover plays its effect", () => {
  it("a slider writes its target at once, with no movement", () => {
    const slider = control("slider", "s", {
      target: [0, null],
      attrs: { label: str("k"), from: num(0), to: num(1), step: none(), ticks: none() },
    });
    const model = page(`<mtp-slider model="m" name="s"></mtp-slider>`, mtpc(variable("k", REAL_0_1, 0), slider));
    const track = input("mtp-slider", "track");
    place(track, 0, 0, 116, 24);
    press(track, 83);
    expect(valueOf(model, "k")).toBe(0.75);
    expect(model.scheduler!.busy()).toBe(false);
  });

  it("a button plays its movement, which takes time", () => {
    const transition = {
      kind: "transition",
      type: "transition",
      access: "scene",
      name: null,
      from: null,
      to: num(1),
      duration: 2,
      ease: null,
      path: null,
    };
    const animation = { kind: "animation", type: "animation", access: "scene", name: null, steps: ["move", [0, null], 1, 2, "linear"] };
    const button = control("button", "go", { animation: 2, attrs: { label: str("go") } });
    const model = page(`<mtp-button model="m" name="go"></mtp-button>`, mtpc(variable("k", REAL_0_1, 0), transition, animation, button));
    input("mtp-button", "button").click();
    expect(valueOf(model, "k")).toBe(0);
    pass(1);
    expect(valueOf(model, "k")).toBeGreaterThan(0.3);
    expect(valueOf(model, "k")).toBeLessThan(0.7);
    pass(1.1);
    expect(valueOf(model, "k")).toBe(1);
  });
});
