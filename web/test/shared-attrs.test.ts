// Shared attribute values (mtp-jru8; docs/mtpc.md, "Shared attribute values"): the file writes a
// value every shape of one kind has once, and the runtime puts it back in each shape.
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("a value every shape of a kind has", () => {
  it("is each shape's own once loaded", () => {
    const rt = load("shared");
    for (const n of ["c0", "c1", "c2"]) expect(rt.value(rt.id(n), "r")).toBe(0.4);
    expect(rt.value(rt.id("c2"), "x")).toBe(2);
  });

  it("is written in one shape without changing the others", () => {
    const rt = load("shared");
    rt.write(rt.id("c1"), "r", 1.5);
    expect([0, 1, 2].map((k) => rt.value(rt.id(`c${k}`), "r"))).toEqual([0.4, 1.5, 0.4]);
  });
});
