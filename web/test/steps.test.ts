// An animation's steps (mtp-76h; docs/reference.md, "Transitions and animations").
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("an animation's steps", () => {
  it("are read while drawing, each for its duration", () => {
    const rt = load("steps");
    expect(rt.value(rt.id("ds"), null)).toEqual([2, 1]);
    rt.write(rt.id("speed"), null, 2);
    expect(rt.value(rt.id("ds"), null)).toEqual([4, 2]);
  });
});
