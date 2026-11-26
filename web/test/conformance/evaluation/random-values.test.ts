// Conformance tests of the rule random-values (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { live } from "../compile.ts";
import { hash, u, RANDOM } from "./shared.ts";

describe("rule random-values: each random function from the seed and its site", () => {
  it("rand from lo to hi", () => {
    const [, v] = live(RANDOM);
    expect(v("b")).toBe(2 + u(7, 1, 0) * (5 - 2));
  });

  it("rand-int from lo to hi, both included", () => {
    const [, v] = live(RANDOM);
    expect(v("c")).toBe(1 + Math.floor(u(7, 2, 0) * 6));
  });

  it("pick", () => {
    const [, v] = live(RANDOM);
    expect(v("d")).toBe([10, 20, 30][Math.floor(u(7, 3, 0) * 3)]);
  });

  it("shuffle", () => {
    const [, v] = live(RANDOM);
    const out = [1, 2, 3, 4];
    for (let i = 3; i > 0; i--) {
      const j = Math.floor(u(7, 4, i) * (i + 1));
      [out[i], out[j]] = [out[j]!, out[i]!];
    }
    expect(v("e")).toEqual(out);
  });

  it("a roll of the dice writes next-seed", () => {
    const [rt, v] = live(`(import rand rand) (rand-seed s 7) (real a (rand))`);
    rt.write(rt.id("s"), null, hash(7, 0x9e3779b9));
    expect(v("a")).toBe(u(hash(7, 0x9e3779b9), 0, 0));
  });

  it.fails("rand-int with lo above hi gives none (mtp-y7vp: rand and rand-int do not check lo and hi)", () => {
    const [rt, v] = live(`(import rand rand-int) (rand-seed s 7) (int lo 1 (>= 0) (<= 10)) (int|none c (rand-int lo 3))`);
    rt.write(rt.id("lo"), null, 10);
    expect(v("c")).toBe(null);
  });
});
