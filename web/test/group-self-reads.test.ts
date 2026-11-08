// A member of a group reading the group itself is recomputed when any member it reads changes,
// those declared after it too (mtp-mnvd).
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("a group read from inside it", () => {
  it("moves a member when one declared after it changes", () => {
    const rt = load("group-self-reads");
    const [v0, v1, v2] = [0, 1, 2].map((i) => rt.id(`v-${i}`)) as [number, number, number];
    expect(rt.value(v0, "y")).toBe(3);
    // v-2 leaves the part v-0 and v-1 are in, so both move.
    rt.write(v2, "part", 1);
    expect(rt.value(v0, "y")).toBe(2);
    expect(rt.value(v1, "y")).toBe(2);
    expect(rt.value(v2, "y")).toBe(1);
  });
});
