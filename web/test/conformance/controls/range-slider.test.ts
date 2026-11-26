// Conformance tests of the rule range-slider (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import { REAL_0_1, control, input, key, maybe, mtpc, none, num, page, place, pointer, str, valueOf, variable } from "./shared.ts";

function range(step: number | null = null) {
  const obj = control("range-slider", "r", {
    low: [0, null],
    high: [1, null],
    attrs: { label: str("band"), from: num(0), to: num(1), step: step === null ? none() : maybe(step), ticks: none() },
  });
  const model = page(`<mtp-range-slider model="m" name="r"></mtp-range-slider>`, mtpc(variable("lo", REAL_0_1, 0.2), variable("hi", REAL_0_1, 0.6), obj));
  // The thumbs' centers run from 8px to 108px: u = (x - 8) / 100.
  place(document.querySelector("mtp-range-slider .mtp-track")!, 0, 0, 116, 24);
  return { model, low: input("mtp-range-slider", "low"), high: input("mtp-range-slider", "high") };
}

const win = window as unknown as Element;

describe("rule range-slider: two thumbs on one track write LOW and HIGH, LOW never above HIGH", () => {
  it("each thumb shows and writes its own target", () => {
    const { model, low, high } = range();
    expect(low.getAttribute("aria-valuenow")).toBe("0.2");
    expect(high.getAttribute("aria-valuenow")).toBe("0.6");
    expect([low.getAttribute("role"), high.getAttribute("role")]).toEqual(["slider", "slider"]);
    pointer(low, "pointerdown", 28);
    pointer(win, "pointermove", 38);
    pointer(win, "pointerup", 38);
    expect(valueOf(model, "lo")).toBeCloseTo(0.3);
    pointer(high, "pointerdown", 68);
    pointer(win, "pointermove", 98);
    pointer(win, "pointerup", 98);
    expect(valueOf(model, "hi")).toBeCloseTo(0.9);
    expect(valueOf(model, "lo")).toBeCloseTo(0.3);
  });

  it("a thumb dragged into the other stops there", () => {
    const { model, low, high } = range();
    pointer(low, "pointerdown", 28);
    pointer(win, "pointermove", 98);
    expect(valueOf(model, "lo")).toBe(0.6);
    pointer(win, "pointerup", 98);
    pointer(high, "pointerdown", 68);
    pointer(win, "pointermove", 0);
    pointer(win, "pointerup", 0);
    expect(valueOf(model, "hi")).toBe(0.6);
  });

  it("an arrow key moves a thumb one step, and not past the other", () => {
    const { model, low, high } = range(0.2);
    key(low, "ArrowRight");
    expect(valueOf(model, "lo")).toBeCloseTo(0.4);
    key(low, "ArrowRight");
    expect(valueOf(model, "lo")).toBeCloseTo(0.6);
    key(low, "ArrowRight");
    expect(valueOf(model, "lo")).toBeCloseTo(0.6);
    key(high, "ArrowLeft");
    expect(valueOf(model, "hi")).toBeCloseTo(0.6);
  });
});
