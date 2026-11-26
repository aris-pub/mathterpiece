// Conformance tests of the rule random-hash (docs/spec/evaluation.md).
import { describe, expect, it } from "vitest";
import { same } from "../../../src/same.ts";
import { live } from "../compile.ts";
import { hash, u, RANDOM } from "./shared.ts";

describe("rule random-hash: the hash of a seed, a site and a number", () => {
  it("gives rand the value u(s, p, 0)", () => {
    const [, v] = live(RANDOM);
    expect(v("a")).toBe(u(7, 0, 0));
  });

  it("uses each number modulo 2^32, so seeds equal modulo 2^32 draw the same values", () => {
    const [rt, v] = live(RANDOM);
    const before = [v("a"), v("b"), v("c"), v("e")];
    rt.write(rt.id("s"), null, 7 + 2 ** 32);
    expect([v("a"), v("b"), v("c"), v("e")]).toEqual(before);
  });
});
