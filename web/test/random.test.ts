// Random values bound to seeds (docs/reference.md, "Random values and seeds"; mtp-bjn0).
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import { nextSeed } from "../src/random.ts";
import { load } from "./helpers.ts";

const sorted = (xs: unknown) => [...(xs as number[])].sort((x, y) => x - y);

describe("random values", () => {
  it("stay in their ranges, and a shuffle keeps its items", () => {
    const rt = load("random");
    const v = (n: string) => rt.value(rt.id(n));
    expect(v("a")).toBeGreaterThanOrEqual(2);
    expect(v("a")).toBeLessThan(3);
    expect([1, 2, 3, 4, 5, 6]).toContain(v("d"));
    expect(sorted(v("order"))).toEqual([1, 2, 3, 4, 5]);
    expect(["x", "y", "z"]).toContain(v("p"));
  });

  it("are the same every time the page loads", () => {
    const [one, two] = [load("random"), load("random")];
    for (const n of ["a", "d", "order", "p", "b", "start"]) expect(one.value(one.id(n))).toEqual(two.value(two.id(n)));
  });

  it("are drawn again when their seed is written, and come back with it", () => {
    const rt = load("random");
    const dots = rt.id("dots");
    const before = rt.value(rt.id("a"));
    rt.write(dots, null, nextSeed(7));
    expect(rt.value(rt.id("a"))).not.toEqual(before);
    rt.write(dots, null, 7);
    expect(rt.value(rt.id("a"))).toEqual(before);
  });

  it("roll the dice: a move of the seed to its next value, which leaves another seed's alone", () => {
    const rt = load("random");
    const b = rt.value(rt.id("b"));
    const start = rt.value(rt.id("start"));
    new Player(rt, rt.id("roll")).seek(0);
    expect(rt.value(rt.id("dots"))).toBe(nextSeed(7));
    expect(rt.value(rt.id("b"))).toBe(b);
    // A free@ start was read once, when the model was built.
    expect(rt.value(rt.id("start"))).toEqual(start);
  });
});
