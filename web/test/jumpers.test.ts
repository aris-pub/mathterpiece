// The arithmetic of the jumpers (docs/spec/controls.md): where a thumb stops, what an arrow key
// moves it by, where the ticks are, what a typed number is, and what a multi-select writes.
import { describe, expect, it } from "vitest";
import {
  type Scale,
  chosenIn,
  fractionOf,
  keyAmount,
  parseNumber,
  snap,
  stepFrom,
  tickValues,
  tidy,
  toggledList,
  valueAt,
} from "../src/jumpers.ts";

const line = (lo: number, hi: number, step: number | null = null, int = false): Scale => ({ lo, hi, step, int, wrap: false });
const ring = (lo: number, hi: number, step: number | null = null, int = false): Scale => ({ lo, hi, step, int, wrap: true });

describe("tidy", () => {
  it("takes off the noise of adding decimals", () => {
    expect(tidy(0.1 + 0.2, 0.1)).toBe(0.3);
    expect(tidy(0.30000000000000004)).toBe(0.3);
    expect(tidy(1 / 3)).toBeCloseTo(1 / 3, 11);
  });
});

describe("a slider's scale", () => {
  it("stops every step from the start", () => {
    const s = line(0, 1, 0.3);
    expect(snap(s, 0.4)).toBe(0.3);
    expect(snap(s, 0.5)).toBe(0.6);
    expect(snap(s, 1)).toBe(0.9);
    expect(snap(s, -1)).toBe(0);
  });

  it("is smooth on a real with no step, and stays between its ends", () => {
    const s = line(0, 2);
    expect(snap(s, 0.123)).toBe(0.123);
    expect(snap(s, 3)).toBe(2);
    expect(keyAmount(s)).toBe(0.02);
  });

  it("stops at each whole number on an int with no step", () => {
    const s = line(0.5, 4.5, null, true);
    expect(snap(s, 2.4)).toBe(2);
    expect(snap(s, 0.6)).toBe(1);
    expect(snap(s, 4.6)).toBe(4);
    expect(keyAmount(s)).toBe(1);
  });

  it("runs from from to to, also when from is the larger", () => {
    const s = line(10, 0, 2);
    expect(valueAt(s, 0)).toBe(10);
    expect(valueAt(s, 1)).toBe(0);
    expect(fractionOf(s, 4)).toBeCloseTo(0.6);
    expect(stepFrom(s, 4, 1)).toBe(2);
  });

  it("moves an arrow key one step, never past an end", () => {
    const s = line(0, 1, 0.25);
    expect(stepFrom(s, 0.5, 1)).toBe(0.75);
    expect(stepFrom(s, 1, 1)).toBe(1);
    expect(stepFrom(s, 0, -1)).toBe(0);
  });

  it("has a tick at each step with no ticks of its own, a tick every ticks with one, and none otherwise", () => {
    expect(tickValues(line(0, 1, 0.25), null)).toEqual([0, 0.25, 0.5, 0.75, 1]);
    expect(tickValues(line(0, 1, 0.1), 0.5)).toEqual([0, 0.5, 1]);
    expect(tickValues(line(0, 1), null)).toEqual([]);
    expect(tickValues(line(0, 1), 0.2)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
  });
});

describe("a dial's scale", () => {
  it("wraps: one full turn covers the interval", () => {
    const d = ring(0, 360);
    expect(valueAt(d, 0.25)).toBe(90);
    expect(snap(d, 370)).toBe(10);
    expect(fractionOf(d, 450)).toBe(0.25);
  });

  it("stops every step from the start, and an arrow key past the end comes round", () => {
    const d = ring(0, 360, 15);
    expect(snap(d, 20)).toBe(15);
    expect(snap(d, 359)).toBe(0);
    expect(stepFrom(d, 345, 1)).toBe(0);
    expect(stepFrom(d, 0, -1)).toBe(345);
  });

  it("stops at each whole number of an int modular type", () => {
    const d = ring(0, 12, null, true);
    expect(snap(d, 11.7)).toBe(0);
    expect(stepFrom(d, 11, 1)).toBe(0);
  });

  it("has its ticks in one turn, the end left out since it is the start", () => {
    expect(tickValues(ring(0, 360, 90), null)).toEqual([0, 90, 180, 270]);
  });
});

describe("a typed number", () => {
  it("is read as a number, with either minus sign", () => {
    expect(parseNumber(" 2.5 ")).toBe(2.5);
    expect(parseNumber("−3")).toBe(-3);
    expect(parseNumber("-3")).toBe(-3);
  });

  it("is nothing when the text is no number", () => {
    expect(parseNumber("")).toBe(null);
    expect(parseNumber("  ")).toBe(null);
    expect(parseNumber("abc")).toBe(null);
    expect(parseNumber("Infinity")).toBe(null);
  });
});

describe("a multi-select's list", () => {
  const options = ["circle", "ellipse", "parabola"];

  it("shows chosen each option that is in the list, and nothing for a value that is no option", () => {
    expect(chosenIn(["parabola", "hyperbola"], options)).toEqual([false, false, true]);
  });

  it("adds an option in the options' order, and removes it when chosen again", () => {
    expect(toggledList(["parabola"], options, 0)).toEqual(["circle", "parabola"]);
    expect(toggledList(["circle", "parabola"], options, 0)).toEqual(["parabola"]);
    expect(toggledList(["parabola", "circle"], options, 1)).toEqual(["circle", "ellipse", "parabola"]);
  });

  it("may become empty", () => {
    expect(toggledList(["circle"], options, 0)).toEqual([]);
  });

  it("compares values by content", () => {
    expect(chosenIn([[1, 2]], [[1, 2], [3, 4]])).toEqual([true, false]);
  });
});
