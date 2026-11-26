// Conformance tests of the rule slider-and-dial (docs/spec/controls.md).
import { describe, expect, it } from "vitest";
import type { Attribute, Type } from "../../../src/doc.ts";
import { ANGLE, HOUR, REAL_0_1, control, input, key, maybe, mtpc, none, num, page, place, pointer, press, str, valueOf, variable } from "./shared.ts";

type Opts = { step?: number; ticks?: number; from?: number; to?: number; type?: Type; value?: number };
const opt = (v: number | undefined): Attribute => (v === undefined ? none() : maybe(v));

function slider(o: Opts = {}) {
  const obj = control("slider", "s", {
    target: [0, null],
    attrs: { label: str("k"), from: num(o.from ?? 0), to: num(o.to ?? 1), step: opt(o.step), ticks: opt(o.ticks) },
  });
  const model = page(`<mtp-slider model="m" name="s"></mtp-slider>`, mtpc(variable("k", o.type ?? REAL_0_1, o.value ?? 0), obj));
  const track = input("mtp-slider", "track");
  // The thumb's center runs from 8px to 108px: u = (x - 8) / 100.
  place(track, 0, 0, 116, 24);
  return { model, track, thumb: input("mtp-slider", "thumb") };
}

function dial(o: Opts = {}) {
  const obj = control("dial", "d", { target: [0, null], attrs: { label: str("theta"), step: opt(o.step), ticks: opt(o.ticks) } });
  const model = page(`<mtp-dial model="m" name="d"></mtp-dial>`, mtpc(variable("theta", o.type ?? ANGLE, o.value ?? 0), obj));
  // A face 100px across, with its center at (50, 50).
  place(document.querySelector("mtp-dial svg")!, 0, 0, 100, 100);
  return { model, ring: input("mtp-dial", "ring"), thumb: input("mtp-dial", "thumb") };
}

const ticksOf = (tag: string) => [...document.querySelectorAll(`${tag} .mtp-ticks [data-value]`)].map((t) => Number(t.getAttribute("data-value")));

describe("rule slider-and-dial: a slider and a dial are one control on two kinds of number", () => {
  it("a click on a slider's track moves the thumb there", () => {
    const { model, track, thumb } = slider();
    press(track, 33);
    expect(valueOf(model, "k")).toBe(0.25);
    expect(thumb.getAttribute("aria-valuenow")).toBe("0.25");
  });

  it("a drag of a slider's thumb writes the value under it at each move", () => {
    const { model, track, thumb } = slider();
    pointer(thumb, "pointerdown", 8);
    pointer(window as unknown as Element, "pointermove", 58);
    expect(valueOf(model, "k")).toBe(0.5);
    pointer(window as unknown as Element, "pointermove", 78);
    expect(valueOf(model, "k")).toBeCloseTo(0.7);
    pointer(window as unknown as Element, "pointerup", 78);
    pointer(window as unknown as Element, "pointermove", 108);
    expect(valueOf(model, "k")).toBeCloseTo(0.7);
    expect(track.closest("mtp-slider")!.hasAttribute("data-mtp-held")).toBe(false);
  });

  it("with a step, a slider's thumb stops every step from the start, and an arrow key moves one step", () => {
    const { model, track, thumb } = slider({ step: 0.25 });
    press(track, 40);
    expect(valueOf(model, "k")).toBe(0.25);
    key(thumb, "ArrowRight");
    expect(valueOf(model, "k")).toBe(0.5);
    key(thumb, "ArrowLeft");
    key(thumb, "ArrowDown");
    expect(valueOf(model, "k")).toBe(0);
    key(thumb, "ArrowUp");
    expect(valueOf(model, "k")).toBe(0.25);
  });

  it("without a step, a slider on a real moves smoothly, an arrow key moving 1/100 of the range", () => {
    const { model, track, thumb } = slider({ from: 0, to: 10, type: "real" });
    press(track, 20.3);
    expect(valueOf(model, "k")).toBeCloseTo(1.23);
    key(thumb, "ArrowRight");
    expect(valueOf(model, "k")).toBeCloseTo(1.33);
  });

  it("without a step, a slider on an int stops at each whole number", () => {
    const { model, track, thumb } = slider({ from: 0, to: 10, type: "int", value: 2 });
    press(track, 44);
    expect(valueOf(model, "k")).toBe(4);
    key(thumb, "ArrowRight");
    expect(valueOf(model, "k")).toBe(5);
  });

  it("a slider has a tick at each step, every ticks with (ticks s), and none with neither", () => {
    slider({ step: 0.25 });
    expect(ticksOf("mtp-slider")).toEqual([0, 0.25, 0.5, 0.75, 1]);
    slider({ step: 0.1, ticks: 0.5 });
    expect(ticksOf("mtp-slider")).toEqual([0, 0.5, 1]);
    slider({ ticks: 0.5 });
    expect(ticksOf("mtp-slider")).toEqual([0, 0.5, 1]);
    slider();
    expect(ticksOf("mtp-slider")).toEqual([]);
  });

  it("a slider shows its target's value when another writer changes it", () => {
    const { model, thumb } = slider();
    const rt = model.runtime!;
    rt.write(rt.id("k"), null, 0.4);
    expect(thumb.getAttribute("aria-valuenow")).toBe("0.4");
    expect(thumb.getAttribute("role")).toBe("slider");
  });

  it("a click on a dial's ring moves the thumb there", () => {
    const { model, ring } = dial();
    press(ring, 100, 50);
    expect(valueOf(model, "theta")).toBe(90);
    press(ring, 50, 100);
    expect(valueOf(model, "theta")).toBe(180);
  });

  it("a drag of a dial's thumb turns it, and past the end it wraps", () => {
    const { model, thumb } = dial();
    pointer(thumb, "pointerdown", 50, 0);
    pointer(window as unknown as Element, "pointermove", 0, 50);
    expect(valueOf(model, "theta")).toBe(270);
    pointer(window as unknown as Element, "pointermove", 49.99, 0);
    pointer(window as unknown as Element, "pointermove", 100, 50);
    expect(valueOf(model, "theta")).toBe(90);
    pointer(window as unknown as Element, "pointerup", 100, 50);
  });

  it("with a step, a dial stops every step, and an arrow key past the end comes round to the start", () => {
    const { model, ring, thumb } = dial({ step: 15, value: 330 });
    key(thumb, "ArrowRight");
    expect(valueOf(model, "theta")).toBe(345);
    key(thumb, "ArrowRight");
    expect(valueOf(model, "theta")).toBe(0);
    press(ring, 100, 45);
    expect(valueOf(model, "theta")).toBe(90);
  });

  it("without a step, a dial on an int modular type stops at each whole number", () => {
    const { model, ring, thumb } = dial({ type: HOUR, value: 11 });
    key(thumb, "ArrowRight");
    expect(valueOf(model, "theta")).toBe(0);
    press(ring, 100, 52);
    expect(valueOf(model, "theta")).toBe(3);
  });

  it("without a step, a dial on a real moves smoothly, an arrow key moving 1/100 of a turn", () => {
    const { model, thumb } = dial({ value: 10 });
    key(thumb, "ArrowLeft");
    expect(valueOf(model, "theta")).toBeCloseTo(6.4);
  });

  it("a dial has a tick at each step, every ticks with (ticks s), and none with neither", () => {
    dial({ step: 90 });
    expect(ticksOf("mtp-dial")).toEqual([0, 90, 180, 270]);
    dial({ step: 15, ticks: 120 });
    expect(ticksOf("mtp-dial")).toEqual([0, 120, 240]);
    dial();
    expect(ticksOf("mtp-dial")).toEqual([]);
  });
});
