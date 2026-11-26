// Conformance tests of the rule toggle (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import { control, input, mtpc, page, str, valueOf, variable } from "./shared.ts";

function toggle(value: boolean) {
  const obj = control("toggle", "t", {
    target: [0, null],
    animation: null,
    attrs: { label: str("show"), value: { type: "bool", bound: ["read", "bool", 0, null, null], deps: [[0, null]] } },
  });
  return page(`<mtp-toggle model="m" name="t"></mtp-toggle>`, mtpc(variable("b", "bool", value), obj));
}

const box = () => input("mtp-toggle", "box") as HTMLInputElement;

describe("rule toggle: a toggle shows its target in a checkbox, and a click writes (not TARGET)", () => {
  it("shows a checkbox with its target's value and its label", () => {
    toggle(true);
    expect(box().type).toBe("checkbox");
    expect(box().checked).toBe(true);
    expect(document.querySelector("mtp-toggle label")!.textContent).toBe("show");
  });

  it("writes (not TARGET) at each click", () => {
    const model = toggle(false);
    box().click();
    expect(valueOf(model, "b")).toBe(true);
    box().click();
    expect(valueOf(model, "b")).toBe(false);
  });

  it("holds no value of its own: it shows the target's value when another writer changes it", () => {
    const model = toggle(false);
    model.runtime!.write(0, null, true);
    expect(box().checked).toBe(true);
    box().click();
    expect(valueOf(model, "b")).toBe(false);
    expect(box().checked).toBe(false);
  });
});
