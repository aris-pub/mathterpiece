// A member of a group is recomputed when a value that it reads changes: the item of a member
// declared after it in a list variable (mtp-mnvd), or an attribute of another member, read through
// the group by a position known when compiling.
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("a group read from inside it", () => {
  it("moves a member when the item of one declared after it changes", () => {
    const rt = load("group-self-reads");
    const [v0, v1, v2] = [0, 1, 2].map((i) => rt.id(`v-${i}`)) as [number, number, number];
    expect(rt.value(v0, "y")).toBe(3);
    // v-2 leaves the part v-0 and v-1 are in, so both move.
    rt.write(rt.id("parts"), null, [0, 0, 1]);
    expect(rt.value(v2, "part")).toBe(1);
    expect(rt.value(v0, "y")).toBe(2);
    expect(rt.value(v1, "y")).toBe(2);
    expect(rt.value(v2, "y")).toBe(1);
  });

  it("moves a member when the member before it changes", () => {
    const rt = load("group-self-reads");
    const [w0, w1, w2] = [0, 1, 2].map((i) => rt.id(`w-${i}`)) as [number, number, number];
    expect(rt.value(w1, "y")).toBe(0);
    // w-1 reads w-0, and w-2 reads w-1.
    rt.write(w0, "part", 4);
    expect(rt.value(w1, "y")).toBe(4);
    expect(rt.value(w2, "y")).toBe(0);
    rt.write(w1, "part", 5);
    expect(rt.value(w2, "y")).toBe(5);
  });
});
