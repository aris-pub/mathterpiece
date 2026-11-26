// Conformance tests of the rule drag-group-shift (docs/spec/core.md).
import { describe, expect, it } from "vitest";
import { drag, group } from "./shared.ts";

describe("rule drag-group-shift: a drag of a group writes its translate (shift-x and shift-y after mtp-1vyc)", () => {
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
