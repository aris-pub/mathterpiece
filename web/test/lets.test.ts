// A let's value is worked out once, however often its name is read (mtp-rjda).
import { describe, expect, it } from "vitest";
import { load } from "./helpers.ts";

describe("let", () => {
  it("works out its value once, so a recursion through it stays linear", () => {
    const t0 = performance.now();
    const rt = load("lets");
    expect(rt.value(rt.id("far"))).toEqual([32768, 0]);
    expect(performance.now() - t0).toBeLessThan(1000);
  });

  it("is read inside a fn, and an inner let may reuse an outer name", () => {
    const rt = load("lets");
    expect(rt.value(rt.id("scaled"))).toEqual([6, 12, 18]);
    expect(rt.value(rt.id("hidden"))).toBe(604);
  });

  it("follows what its value reads", () => {
    const rt = load("lets");
    rt.write(rt.id("m"), null, 5);
    expect(rt.value(rt.id("scaled"))).toEqual([10, 20, 30]);
    expect(rt.value(rt.id("hidden"))).toBe(1006);
  });
});
