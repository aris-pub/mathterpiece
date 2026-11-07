// A let whose body holds declarations works out each value once, where it is written (mtp-gvrf.2).
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("a let holding declarations", () => {
  it("gives every shape that reads it the same value", () => {
    const rt = load("body-lets");
    expect(rt.value(rt.id("line"), "points")).toEqual([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]]);
    expect(rt.value(rt.id("d3"), "pos")).toEqual([3, 0]);
  });

  it("follows what its value reads", () => {
    const rt = load("body-lets");
    rt.write(rt.id("m"), null, 2);
    expect(rt.value(rt.id("line"), "points")).toEqual([[0, 0], [2, 0], [4, 0], [6, 0], [8, 0]]);
    expect(rt.value(rt.id("d4"), "pos")).toEqual([8, 0]);
  });

  it("holds its own value in each foreach copy", () => {
    const rt = load("body-lets");
    rt.write(rt.id("m"), null, 2);
    expect([0, 1, 2].map((i) => rt.value(rt.id(`w${i}`), "r"))).toEqual([2, 4, 6]);
  });

  it("holds its own value in each motif instance", () => {
    const rt = load("body-lets");
    rt.write(rt.id("m"), null, 2);
    expect(rt.value(rt.id("p.a"), "r")).toBe(4);
    expect(rt.value(rt.id("p.b"), "x")).toBe(4);
    expect(rt.value(rt.id("q.a"), "r")).toBe(6);
  });

  it("keeps the values it holds out of the variables", () => {
    const rt = load("body-lets");
    const held = rt.objects.filter((o) => o.kind === "variable" && o.let !== undefined);
    expect(held.map((o) => o.let).sort()).toEqual(["pts", "v", "v", "w", "w", "w"]);
    expect(held.every((o) => o.name === null)).toBe(true);
  });
});
