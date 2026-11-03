// Dragging (docs/reference.md, "Dragging").
import { describe, expect, it } from "vitest";
import { Drags } from "../src/drag.ts";
import type { Runtime } from "../src/runtime.ts";
import { load } from "./helpers.ts";

function setup(): [Runtime, Drags, (name: string, attr?: string) => unknown] {
  const rt = load("page");
  return [rt, new Drags(rt), (name, attr) => rt.value(rt.id(name), attr ?? null)];
}

describe("a drag", () => {
  it("moves a shape's own position with the pointer, keeping the offset of the press", () => {
    const [rt, drags, v] = setup();
    expect(drags.grab(rt.id("dot"), [1.5, 1])).toBe(true);
    drags.move([2.5, 3]);
    expect(v("dot", "pos")).toEqual([2, 3]);
  });

  it("finds the value of a number the position depends on that brings it closest", () => {
    const [rt, drags, v] = setup();
    drags.grab(rt.id("orbit"), [2, 0]);
    drags.move([0, 2]);
    expect(v("k") as number).toBeCloseTo(10, 0);
  });

  it("tells the page once per pointer move, however many values it tries", () => {
    // Each change redraws every canvas, so the search's own writes must not each tell the page.
    const [rt, drags, v] = setup();
    let told = 0;
    rt.onChange(() => told++);
    drags.grab(rt.id("orbit"), [2, 0]);
    drags.move([0, 2]);
    expect(told).toBe(1);
    expect(v("k") as number).toBeCloseTo(10, 0);
  });

  it("moves every member of a group", () => {
    const [rt, drags, v] = setup();
    drags.grab(rt.id("p1"), [0, 0]);
    drags.move([1, 1]);
    expect([v("p1", "pos"), v("p2", "pos")]).toEqual([
      [1, 1],
      [2, 1],
    ]);
  });

  it("clamps each write to its conditions", () => {
    const [rt, drags, v] = setup();
    drags.grab(rt.id("limited"), [0, 0]);
    drags.move([5, 0]);
    expect(v("limited", "x")).toBe(2);
  });

  it("moves an int target by whole steps", () => {
    // mtp-q44: the search used to step by 1e-6, which the write into an int rounds away.
    const [rt, drags, v] = setup();
    drags.grab(rt.id("stepper"), [0, 0]);
    drags.move([3.2, 0]);
    expect(v("steps")).toBe(3);
  });

  it("moves a target that starts at its upper limit", () => {
    // mtp-n8j: the search used to step only upward, which the limit undoes.
    const [rt, drags, v] = setup();
    drags.grab(rt.id("edge"), [10, 5]);
    drags.move([7, 5]);
    expect(v("top") as number).toBeCloseTo(7, 6);
  });
});
