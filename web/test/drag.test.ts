import { describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { Drags } from "../src/drag.ts";
import { Runtime } from "../src/runtime.ts";

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, fill: "red", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };

// u (2) is a circle at (0, 1); p (3) is a motif at (5, 0) turned 90 degrees, holding head (4) and
// stem (5). Listeners come after, from 6 on.
function world(listeners: Omit<Obj, "id" | "name" | "attrs">[], extra: Omit<Obj, "id">[] = []) {
  const objects: Omit<Obj, "id">[] = [
    { kind: "canvas", name: "view", attrs: { "view-x": -10, "view-y": -10, "view-width": 20, "view-height": 20, transform: ID }, shows: [1] },
    { kind: "root", name: "s", attrs: { transform: ID }, members: [2, 3] },
    { kind: "circle", name: "u", parent: 1, attrs: { ...style, x: 0, y: 1, r: 0.5 } },
    { kind: "motif", name: "p", motif: "pin", parent: 1, members: [4, 5], params: {}, attrs: { transform: [0, -1, 0, 1, 0, 0], x: 5, y: 0, opacity: 1 } },
    { kind: "circle", name: "head", parent: 3, attrs: { ...style, x: 0, y: 0, r: 0.2 } },
    { kind: "line", name: "stem", parent: 3, attrs: { ...style, x: 0, y: 0, x1: 0, y1: 0, x2: 0, y2: -1 } },
    ...listeners.map((l) => ({ name: null, attrs: {}, ...l })),
    ...extra,
  ];
  const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
  const rt = new Runtime(doc);
  return { rt, drags: new Drags(rt) };
}

const on = (node: number, conditions: unknown[] = [], when: unknown = null, attr = "pos") => ({
  kind: "on-drag",
  target: [node, attr] as [number, string],
  conditions,
  when,
});
const pos = (rt: Runtime, i: number) => [rt.value(i, "x"), rt.value(i, "y")];

describe("dragging", () => {
  it("moves the node by the pointer's motion, without jumping to the pointer", () => {
    const { rt, drags } = world([on(2)]);
    expect(drags.grab(2, [0.3, 1.2])).toBe(true);
    drags.move([1.3, 2.2]);
    expect(pos(rt, 2)).toEqual([1, 2]);
  });

  it("moves a motif, and its members come along", () => {
    const { rt, drags } = world([on(3)]);
    drags.grab(4, [5, 0]);
    drags.move([6, 2]);
    expect(pos(rt, 3)).toEqual([6, 2]);
    const [x, y] = rt.point(4);
    expect([x, y]).toEqual([6, 2]);
  });

  it("goes up the tree to the nearest node with a listener", () => {
    const { rt, drags } = world([on(3), on(4)]);
    drags.grab(5, [5, 0]);
    drags.move([6, 0]);
    expect(pos(rt, 3)).toEqual([6, 0]);
    drags.release();
    drags.grab(4, [6, 0]);
    drags.move([6, 1]);
    expect(pos(rt, 3)).toEqual([6, 0]);
  });

  it("writes in the parent's frame", () => {
    const { rt, drags } = world([on(4)]);
    drags.grab(4, [5, 0]);
    drags.move([5, 1]);
    const [x, y] = pos(rt, 4);
    expect(x).toBeCloseTo(1);
    expect(y).toBeCloseTo(0);
  });

  it("moves only its target", () => {
    const { rt, drags } = world([on(2, [], null, "x")]);
    drags.grab(2, [0, 1]);
    drags.move([2, 5]);
    expect(pos(rt, 2)).toEqual([2, 1]);
  });

  it("grabs nothing without a listener", () => {
    const { drags } = world([on(3)]);
    expect(drags.grab(2, [0, 1])).toBe(false);
    expect(drags.draggable(2)).toBe(false);
    expect(drags.draggable(5)).toBe(true);
  });

  it("rejects a move where a condition fails, leaving the node at the last accepted spot", () => {
    const { rt, drags } = world([on(2, [["<=", ["read", 2, "x", null], 2]])]);
    drags.grab(2, [0, 1]);
    drags.move([1.5, 1]);
    drags.move([3, 1]);
    expect(pos(rt, 2)).toEqual([1.5, 1]);
    drags.move([1, 0]);
    expect(pos(rt, 2)).toEqual([1, 0]);
  });

  it("detaches a listener while its when does not hold, so the press goes further up", () => {
    const flag = { kind: "real", name: "live", attrs: { value: 0 } };
    const { rt, drags } = world([on(3), on(4, [], [">", ["read", 8, "value"], 0])], [flag]);
    drags.grab(4, [5, 0]);
    drags.move([6, 0]);
    expect(pos(rt, 3)).toEqual([6, 0]);
    drags.release();
    rt.write(8, "value", 1);
    drags.grab(4, [6, 0]);
    drags.move([6, 1]);
    expect(pos(rt, 3)).toEqual([6, 0]);
  });

  it("reads when as a state", () => {
    const state = { kind: "state", name: "on", attrs: {}, conditions: [[">", ["read", 2, "x"], 0]], moves: null };
    const { drags } = world([on(2, [], ["holds", 7])], [state]);
    expect(drags.grab(2, [0, 1])).toBe(false);
  });
});
