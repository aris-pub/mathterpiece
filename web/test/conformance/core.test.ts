// Conformance tests for docs/spec/core.md: what only the runtime can show. A test that today's
// code fails, by a "Code differs" note of the spec, is written with it.fails and names the bead.
import { describe, expect, it } from "vitest";
import { Drags } from "../../src/drag.ts";
import { live } from "./compile.ts";

type Point = [number, number];

/** Drags the shape named by hit from one point of the scene to another. */
function drag(source: string, hit: string, from: Point, to: Point) {
  const [rt, v] = live(source);
  const drags = new Drags(rt);
  expect(drags.grab(rt.id(hit), from)).toBe(true);
  drags.move(to);
  drags.release();
  return v;
}

const group = (items: string, listener: string) =>
  `(scene s (group g ${items} (circle c (x 1) (r 1))))\n(canvas v s (${listener}))`;

describe("rule drag-group-translate: a drag of a group writes its translate", () => {
  it.fails("a group that is not fixed-size (mtp-ydd4.7.36: the runtime moves each member)", () => {
    const v = drag(group("", "on-drag g g.pos"), "c", [1, 0], [3, 1]);
    expect(v("g", "translate")).toEqual([2, 1]);
    expect(v("c", "pos")).toEqual([1, 0]);
  });

  it("a fixed-size group", () => {
    const v = drag(group("(fixed-size true)", "on-drag g g.pos"), "c", [1, 0], [3, 1]);
    expect(v("g", "translate")).toEqual([2, 1]);
    expect(v("c", "pos")).toEqual([1, 0]);
  });

  it.fails("a move of the group's pos (mtp-ydd4.7.36: the runtime writes the group's x and y)", () => {
    const v = drag(group("", "on-drag g (move g.pos (to pointer))"), "c", [1, 0], [3, 1]);
    expect(v("g", "translate")).toEqual([2, 1]);
    expect(v("c", "pos")).toEqual([1, 0]);
  });

  it.fails("a move of the group's x (mtp-ydd4.7.36: the runtime writes the group's x)", () => {
    const v = drag(group("", "on-drag g (move g.x (to (. pointer 0)))"), "c", [1, 0], [3, 1]);
    expect(v("g", "translate")).toEqual([2, 0]);
  });
});

const SHAPE = "(scene s (circle p (x 1) (y 1) (r 1)))\n";

describe("rule sugar-rewrites: a drag written with a name means its move", () => {
  const cases: [string, string, string][] = [
    ["pos", "on-drag p p.pos", "on-drag p (move p.pos (to pointer))"],
    ["x", "on-drag p p.x", "on-drag p (move p.x (to (. pointer 0)))"],
    ["y", "on-drag p p.y", "on-drag p (move p.y (to (. pointer 1)))"],
  ];
  for (const [what, short, long] of cases) {
    it(`a drag of ${what}`, () => {
      const a = drag(`${SHAPE}(canvas v s (${short}))`, "p", [1.5, 1], [3, 4]);
      const b = drag(`${SHAPE}(canvas v s (${long}))`, "p", [1.5, 1], [3, 4]);
      expect(a("p", "pos")).toEqual(b("p", "pos"));
    });
  }
});
