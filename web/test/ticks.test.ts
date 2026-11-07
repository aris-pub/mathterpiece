// A slider's ticks: round values across its range, placed where the knob stands for them.
import { describe, expect, it } from "vitest";
import { niceTicks, placeTicks } from "../src/ticks.ts";

describe("niceTicks", () => {
  it("picks round values, about five, across the range", () => {
    expect(niceTicks(0, 0.04)).toEqual([0, 0.01, 0.02, 0.03, 0.04]);
    expect(niceTicks(0, 360)).toEqual([0, 100, 200, 300]);
    expect(niceTicks(-2, 2)).toEqual([-2, -1, 0, 1, 2]);
    expect(niceTicks(0, 1)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
  });

  it("works for a range given backwards, and gives none for an empty one", () => {
    expect(niceTicks(1, 0)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
    expect(niceTicks(3, 3)).toEqual([]);
  });

  it("writes no float noise and no negative zero", () => {
    const t = niceTicks(-0.3, 0.3);
    expect(t).toContain(0);
    expect(t.every((v) => String(v).length <= 5)).toBe(true);
    expect(Object.is(t[t.indexOf(0)], -0)).toBe(false);
  });
});

describe("placeTicks", () => {
  it("places each tick where the knob gives its value, for a straight range", () => {
    const at = (u: number) => 10 + 30 * u;
    expect(placeTicks(at).map((t) => [t.value, +t.u.toFixed(6)])).toEqual([
      [10, 0], [20, 0.333333], [30, 0.666667], [40, 1],
    ]);
  });

  it("follows an eased range, and a range that runs backwards", () => {
    const eased = placeTicks((u) => 100 * u * u);
    expect(eased.find((t) => t.value === 20)!.u).toBeCloseTo(Math.sqrt(0.2), 6);
    const down = placeTicks((u) => 1 - u);
    expect(down.find((t) => t.value === 0.2)!.u).toBeCloseTo(0.8, 6);
  });

  it("gives no ticks for a value that is not a number", () => {
    expect(placeTicks(() => [1, 2])).toEqual([]);
  });
});
