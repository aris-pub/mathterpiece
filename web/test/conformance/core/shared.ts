// What the conformance tests of docs/spec/core.md share.
import { expect } from "vitest";
import { Drags } from "../../../src/drag.ts";
import { live } from "../compile.ts";

export type Point = [number, number];

/** Drags the shape named by hit from one point of the scene to another. */

export function drag(source: string, hit: string, from: Point, to: Point) {
  const [rt, v] = live(source);
  const drags = new Drags(rt);
  expect(drags.grab(rt.id(hit), from)).toBe(true);
  drags.move(to);
  drags.release();
  return v;
}

export const group = (items: string, listener: string) =>
  `(scene s (group g ${items} (circle c (x 1) (r 1))))\n(canvas v s (${listener}))`;

export const SHAPE = "(scene s (circle p (x 1) (y 1) (r 1)))\n";
