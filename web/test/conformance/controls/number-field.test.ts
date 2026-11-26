// Conformance tests of the rule number-field (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import type { Type } from "../../../src/doc.ts";
import { bool, control, hasInput, input, key, mtpc, num, page, pointer, str, typeInto, valueOf, variable } from "./shared.ts";

type Opts = { step?: number; buttons?: boolean; typing?: boolean; type?: Type; value?: number };

function field(o: Opts = {}) {
  const obj = control("number-field", "f", {
    target: [0, null],
    attrs: { label: str("sides"), step: num(o.step ?? 1), buttons: bool(o.buttons ?? true), typing: bool(o.typing ?? true) },
  });
  const type = o.type ?? { refine: "real", constraints: [[">=", 0], ["<=", 1000]] };
  return page(`<mtp-number-field model="m" name="f"></mtp-number-field>`, mtpc(variable("n", type, o.value ?? 5), obj));
}

const box = () => input("mtp-number-field", "box") as HTMLInputElement;
const enter = (el: Element) => key(el, "Enter");
const outlined = () => document.querySelector("mtp-number-field .mtp-refused") !== null;
const told = () => document.querySelector("mtp-number-field [aria-live]")!.textContent ?? "";
const win = window as unknown as Element;

describe("rule number-field: a number field changes by typing, buttons, arrow keys and scrubbing", () => {
  it("shows its target's value, as a spin button", () => {
    const model = field();
    expect(box().value).toBe("5.0");
    expect(box().getAttribute("role")).toBe("spinbutton");
    expect(box().getAttribute("aria-valuenow")).toBe("5");
    model.runtime!.write(0, null, 7);
    expect(box().value).toBe("7.0");
  });

  it("writes a typed value only when it is committed: with Enter, or by leaving the field", () => {
    const model = field();
    typeInto(box(), "12");
    expect(valueOf(model, "n")).toBe(5);
    expect(box().value).toBe("12");
    enter(box());
    expect(valueOf(model, "n")).toBe(12);
    typeInto(box(), "13");
    box().dispatchEvent(new Event("blur"));
    expect(valueOf(model, "n")).toBe(13);
    expect(outlined()).toBe(false);
  });

  it("adds or subtracts the step with the buttons, and ten steps with Shift", () => {
    const model = field({ step: 0.5 });
    input("mtp-number-field", "plus").click();
    expect(valueOf(model, "n")).toBe(5.5);
    input("mtp-number-field", "minus").click();
    input("mtp-number-field", "minus").click();
    expect(valueOf(model, "n")).toBe(4.5);
    input("mtp-number-field", "plus").dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: true }));
    expect(valueOf(model, "n")).toBe(9.5);
  });

  it("adds or subtracts the step with the arrow keys, and ten steps with Shift", () => {
    const model = field({ step: 0.1, value: 1 });
    key(box(), "ArrowUp");
    expect(valueOf(model, "n")).toBe(1.1);
    key(box(), "ArrowDown", { shiftKey: true });
    expect(valueOf(model, "n")).toBe(0.1);
  });

  it("changes by one step every few pixels of a drag sideways on its label, ten with Shift", () => {
    const model = field();
    const label = input("mtp-number-field", "scrub");
    pointer(label, "pointerdown", 100);
    pointer(win, "pointermove", 140);
    const after = valueOf(model, "n") as number;
    expect(after).toBeGreaterThan(5);
    expect(Number.isInteger(after)).toBe(true);
    pointer(win, "pointermove", 100);
    expect(valueOf(model, "n")).toBe(5);
    pointer(win, "pointermove", 140, 0, { shiftKey: true });
    expect(valueOf(model, "n")).toBe(5 + 10 * (after - 5));
    pointer(win, "pointerup", 140);
    pointer(win, "pointermove", 400);
    expect(valueOf(model, "n")).toBe(5 + 10 * (after - 5));
  });

  it("is not changed by the mouse wheel", () => {
    const model = field();
    box().dispatchEvent(new WheelEvent("wheel", { deltaY: -100, bubbles: true, cancelable: true }));
    expect(valueOf(model, "n")).toBe(5);
  });

  it("with (buttons false) has no buttons", () => {
    field({ buttons: false });
    expect(hasInput("mtp-number-field", "plus")).toBe(false);
    expect(hasInput("mtp-number-field", "minus")).toBe(false);
    expect(hasInput("mtp-number-field", "box")).toBe(true);
  });

  it("with (typing false) shows the value as plain text, which the arrow keys still change", () => {
    const model = field({ typing: false });
    expect(hasInput("mtp-number-field", "box")).toBe(false);
    expect(document.querySelector("mtp-number-field input")).toBe(null);
    const value = input("mtp-number-field", "value");
    expect(value.textContent).toBe("5.0");
    expect(value.getAttribute("role")).toBe("spinbutton");
    expect(value.classList.contains("mtp-scrub")).toBe(false);
    key(value, "ArrowUp");
    expect(valueOf(model, "n")).toBe(6);
  });

  it("with neither buttons nor typing underlines the value to show that it can be scrubbed", () => {
    const model = field({ buttons: false, typing: false });
    const value = input("mtp-number-field", "value");
    expect(value.classList.contains("mtp-scrub")).toBe(true);
    pointer(value, "pointerdown", 0);
    pointer(win, "pointermove", 200);
    pointer(win, "pointerup", 200);
    expect(valueOf(model, "n") as number).toBeGreaterThan(5);
  });

  it("after a commit that is brought into range shows the target's value, a red outline, and tells a screen reader", () => {
    const model = field();
    typeInto(box(), "2500");
    enter(box());
    expect(valueOf(model, "n")).toBe(1000);
    expect(box().value).toBe("1000.0");
    expect(outlined()).toBe(true);
    expect(told()).toContain("2500");
  });

  it("after a commit that is refused shows the target's value and a red outline", () => {
    const model = field();
    typeInto(box(), "many");
    enter(box());
    expect(valueOf(model, "n")).toBe(5);
    expect(box().value).toBe("5.0");
    expect(outlined()).toBe(true);
    expect(told()).toContain("many");
  });
});
