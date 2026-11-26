// Conformance tests of the rule sugar-rewrites (docs/spec/core.md).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { Drags } from "../../../src/drag.ts";
import { live } from "../compile.ts";
import { type Point, SHAPE } from "./shared.ts";

const POINTS = fc.tuple(fc.double({ min: -50, max: 50, noNaN: true }), fc.double({ min: -50, max: 50, noNaN: true }));
// Where the pointer grabs p, from its center: inside p, whose radius is 1.
const OFFSETS = fc.tuple(fc.double({ min: -0.7, max: 0.7, noNaN: true }), fc.double({ min: -0.7, max: 0.7, noNaN: true }));

describe("rule sugar-rewrites: a drag written with a name means its move", () => {
  const cases: [string, string, string][] = [
    ["pos", "on-drag p p.pos", "on-drag p (move p.pos (to pointer))"],
    ["x", "on-drag p p.x", "on-drag p (move p.x (to (. pointer 0)))"],
    ["y", "on-drag p p.y", "on-drag p (move p.y (to (. pointer 1)))"],
  ];
  for (const [what, short, long] of cases) {
    // Each drag grabs p near its center, wherever the drags before it left p.
    it(`a drag of ${what}`, () => {
      const models = [short, long].map((listener) => {
        const [rt, v] = live(`${SHAPE}(canvas v s (${listener}))`);
        return { rt, v, drags: new Drags(rt) };
      });
      fc.assert(
        fc.property(fc.array(fc.tuple(OFFSETS, POINTS), { minLength: 1, maxLength: 4 }), (motions) => {
          for (const [[dx, dy], to] of motions) {
            for (const { rt, v, drags } of models) {
              const [x, y] = v("p", "pos") as Point;
              expect(drags.grab(rt.id("p"), [x + dx, y + dy])).toBe(true);
              drags.move(to);
              drags.release();
            }
            expect(models[0]!.v("p", "pos")).toEqual(models[1]!.v("p", "pos"));
          }
        }),
        { numRuns: 200, examples: [[[[[0.5, 0], [3, 4]]]]] },
      );
    });
  }
});
