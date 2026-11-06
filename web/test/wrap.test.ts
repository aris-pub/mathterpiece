// Values that wrap (mtp-y2d; docs/type-system.md, 5.b): every write is brought into [lo, hi).
import { describe, expect, it } from "vitest";
import { wrapInto } from "../src/builtins.ts";
import { Player } from "../src/player.ts";
import { load } from "./helpers.ts";

function setup() {
  const rt = load("wrap");
  return { rt, v: (name: string) => rt.value(rt.id(name), null) as number };
}

describe("a value that wraps", () => {
  it("brings every write into its interval", () => {
    const { rt, v } = setup();
    rt.write(rt.id("theta"), null, 370);
    expect(v("theta")).toBe(10);
    rt.write(rt.id("theta"), null, -10);
    expect(v("theta")).toBe(350);
    rt.write(rt.id("theta"), null, 360);
    expect(v("theta")).toBe(0);
  });

  it("rounds an int before it wraps", () => {
    const { rt, v } = setup();
    rt.write(rt.id("hour"), null, 11.6);
    expect(v("hour")).toBe(0);
    rt.write(rt.id("hour"), null, 25);
    expect(v("hour")).toBe(1);
  });

  it("brings a bound value into its interval", () => {
    const { rt, v } = setup();
    rt.write(rt.id("theta"), null, 200);
    expect(v("double")).toBe(40);
  });

  it("turns all the way round when moved by a full turn", () => {
    const { rt, v } = setup();
    const p = new Player(rt, rt.id("turn"));
    p.seek(0.5);
    expect(v("theta")).toBeCloseTo(220);
    p.seek(0.9);
    expect(v("theta")).toBeCloseTo(4);
    p.seek(1);
    expect(v("theta")).toBeCloseTo(40);
  });

  it("goes through the numbers as written, from 350 back to 10", () => {
    const { rt, v } = setup();
    const p = new Player(rt, rt.id("back"));
    p.seek(0.5);
    expect(v("theta")).toBeCloseTo(180);
  });

  it("never lands on the top of its interval", () => {
    expect(wrapInto(-1e-17, 0, 360)).toBe(0);
    expect(wrapInto(725, 0, 360)).toBe(5);
  });
});
