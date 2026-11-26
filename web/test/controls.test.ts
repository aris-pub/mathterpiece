// The author's decisions of 2026-11-26 on the jumpers, which docs/spec/controls.md does not state
// yet: a press on a range slider's track, the arrow keys and Escape in a number field and a text
// field, and the placeholder of a menu. The look of the checkboxes and radio buttons is tested in
// test/browser/jumpers.test.ts, since happy-dom does not apply CSS.
import { describe, expect, it } from "vitest";
import {
  REAL_0_1,
  bool,
  control,
  input,
  mtpc,
  none,
  num,
  page,
  place,
  pointer,
  str,
  typeInto,
  valueOf,
  variable,
} from "./conformance/controls/shared.ts";

const win = window as unknown as Element;

/** A keydown on el, which tells whether a handler prevented its default. */
function keyDown(el: Element, k: string, init: KeyboardEventInit = {}): boolean {
  const e = new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true, ...init });
  el.dispatchEvent(e);
  return e.defaultPrevented;
}

describe("a press on a range slider's track away from both thumbs", () => {
  function range(lo: number, hi: number) {
    const obj = control("range-slider", "r", {
      low: [0, null],
      high: [1, null],
      attrs: { label: str("band"), from: num(0), to: num(1), step: none(), ticks: none() },
    });
    const model = page(`<mtp-range-slider model="m" name="r"></mtp-range-slider>`, mtpc(variable("lo", REAL_0_1, lo), variable("hi", REAL_0_1, hi), obj));
    // The thumbs' centers run from 8px to 108px: u = (x - 8) / 100.
    const track = document.querySelector("mtp-range-slider .mtp-track")!;
    place(track, 0, 0, 116, 24);
    return { model, track, low: input("mtp-range-slider", "low"), high: input("mtp-range-slider", "high") };
  }

  it("moves the nearer thumb there, and gives it the focus", () => {
    const { model, track, low, high } = range(0.2, 0.6);
    pointer(track, "pointerdown", 18);
    pointer(win, "pointerup", 18);
    expect(valueOf(model, "lo")).toBeCloseTo(0.1);
    expect(valueOf(model, "hi")).toBeCloseTo(0.6);
    expect(document.activeElement).toBe(low);
    pointer(track, "pointerdown", 98);
    pointer(win, "pointerup", 98);
    expect(valueOf(model, "hi")).toBeCloseTo(0.9);
    expect(document.activeElement).toBe(high);
    pointer(track, "pointerdown", 48);
    pointer(win, "pointerup", 48);
    expect(valueOf(model, "lo")).toBeCloseTo(0.4);
    expect(valueOf(model, "hi")).toBeCloseTo(0.9);
  });

  it("goes on as a drag of that thumb until the release", () => {
    const { model, track } = range(0.2, 0.6);
    pointer(track, "pointerdown", 98);
    pointer(win, "pointermove", 78);
    expect(valueOf(model, "hi")).toBeCloseTo(0.7);
    pointer(win, "pointermove", 0);
    expect(valueOf(model, "hi")).toBeCloseTo(0.2);
    pointer(win, "pointerup", 0);
    expect(valueOf(model, "lo")).toBeCloseTo(0.2);
  });

  it("moves the thumb on its side when both thumbs are on one spot", () => {
    const { model, track } = range(0.5, 0.5);
    pointer(track, "pointerdown", 88);
    pointer(win, "pointerup", 88);
    expect([valueOf(model, "lo"), valueOf(model, "hi")]).toEqual([0.5, 0.8]);
    const again = range(0.5, 0.5);
    pointer(again.track, "pointerdown", 28);
    pointer(win, "pointerup", 28);
    expect([valueOf(again.model, "lo"), valueOf(again.model, "hi")]).toEqual([0.2, 0.5]);
  });
});

describe("the arrow keys in a number field", () => {
  function field() {
    const obj = control("number-field", "f", {
      target: [0, null],
      attrs: { label: str("sides"), step: num(1), buttons: bool(true), typing: bool(true) },
    });
    return page(`<mtp-number-field model="m" name="f"></mtp-number-field>`, mtpc(variable("n", "real", 5), obj));
  }
  const box = () => input("mtp-number-field", "box") as HTMLInputElement;

  it("move the text cursor, and do not step the value, while the box holds typed text not yet committed", () => {
    const model = field();
    typeInto(box(), "12");
    expect(keyDown(box(), "ArrowUp")).toBe(false);
    expect(keyDown(box(), "ArrowDown", { shiftKey: true })).toBe(false);
    expect(valueOf(model, "n")).toBe(5);
    expect(box().value).toBe("12");
  });

  it("step the value again once the typed text is committed", () => {
    const model = field();
    typeInto(box(), "12");
    keyDown(box(), "Enter");
    expect(keyDown(box(), "ArrowUp")).toBe(true);
    expect(valueOf(model, "n")).toBe(13);
  });
});

describe("Escape in a number field or a text field", () => {
  it("puts back the number field's value and drops the typed text", () => {
    const obj = control("number-field", "f", {
      target: [0, null],
      attrs: { label: str("sides"), step: num(1), buttons: bool(true), typing: bool(true) },
    });
    const model = page(`<mtp-number-field model="m" name="f"></mtp-number-field>`, mtpc(variable("n", "real", 5), obj));
    const box = input("mtp-number-field", "box") as HTMLInputElement;
    typeInto(box, "12");
    expect(keyDown(box, "Escape")).toBe(true);
    expect(box.value).toBe("5.0");
    box.dispatchEvent(new Event("blur"));
    expect(valueOf(model, "n")).toBe(5);
    expect(document.querySelector("mtp-number-field .mtp-refused")).toBe(null);
    // With the typed text dropped, the arrow keys step the value.
    keyDown(box, "ArrowUp");
    expect(valueOf(model, "n")).toBe(6);
  });

  function textField() {
    const obj = control("text-field", "t", { target: [0, null], attrs: { label: str("name") } });
    return page(`<mtp-text-field model="m" name="t"></mtp-text-field>`, mtpc(variable("word", "string", "circle"), obj));
  }

  it("puts back the text field's string and drops the typed text", () => {
    const model = textField();
    const box = input("mtp-text-field", "box") as HTMLInputElement;
    typeInto(box, "square");
    expect(keyDown(box, "Escape")).toBe(true);
    expect(box.value).toBe("circle");
    box.dispatchEvent(new Event("blur"));
    expect(valueOf(model, "word")).toBe("circle");
    expect(document.querySelector("mtp-text-field .mtp-refused")).toBe(null);
  });

  it("puts back the value that the target holds now, after another writer changed it", () => {
    const model = textField();
    const box = input("mtp-text-field", "box") as HTMLInputElement;
    typeInto(box, "squ");
    model.runtime!.write(0, null, "ellipse");
    keyDown(box, "Escape");
    expect(box.value).toBe("ellipse");
  });
});

describe("a menu with nothing chosen", () => {
  const OPTIONS = [{ value: str("circle") }, { value: str("ellipse") }];

  function menu(many: boolean, label: string, value: unknown) {
    const kind = many ? "multi-select" : "select";
    const obj = control(kind, "pick", { target: [0, null], as: "menu", options: OPTIONS, attrs: { label: str(label) } });
    const type = many ? { list: "string" as const } : "string";
    page(`<mtp-${kind} model="m" name="pick"></mtp-${kind}>`, mtpc(variable("curve", type, value), obj));
    return input(`mtp-${kind}`, "menu");
  }

  it("shows the select's label in its button as a placeholder, unseen by a screen reader, until an option is chosen", () => {
    const button = menu(false, "curve", "line");
    const placeholder = button.querySelector(".mtp-placeholder")!;
    expect(placeholder.textContent).toBe("curve");
    expect(placeholder.getAttribute("aria-hidden")).toBe("true");
    button.click();
    input("mtp-select", "option-2").click();
    expect(button.querySelector(".mtp-placeholder")).toBe(null);
    expect(button.textContent).toBe("ellipse");
  });

  it("shows the multi-select's label in its button as a placeholder when its list is empty", () => {
    const button = menu(true, "curves", []);
    expect(button.querySelector(".mtp-placeholder")!.textContent).toBe("curves");
    button.click();
    input("mtp-multi-select", "option-1").click();
    expect(button.textContent).toBe("circle");
    input("mtp-multi-select", "option-1").click();
    expect(button.querySelector(".mtp-placeholder")!.textContent).toBe("curves");
  });

  it("shows nothing when the control has no label", () => {
    expect(menu(false, "", "line").textContent).toBe("");
    expect(menu(true, "", []).textContent).toBe("");
  });
});
