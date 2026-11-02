// Dragging (docs/reference.md, "Dragging").
import { describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { Drags } from "../src/drag.ts";
import { Runtime } from "../src/runtime.ts";

const docs = import.meta.glob("./data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });

function setup(): [Runtime, Drags, (name: string, attr?: string) => unknown] {
  const rt = new Runtime(JSON.parse(docs["./data/runtime/page.mtpc"] as string) as Doc);
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
});
