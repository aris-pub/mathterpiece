// What the conformance tests of docs/spec/evaluation.md share.
import { live } from "../compile.ts";

export function hash(...xs: number[]): number {
  let h = 0x811c9dc5;
  for (const x of xs) {
    const word = ((x % 2 ** 32) + 2 ** 32) % 2 ** 32;
    h = Math.imul((h ^ word) >>> 0, 0x01000193) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
    h = Math.imul(h, 0x2c1b3c6d) >>> 0;
    h = (h ^ (h >>> 12)) >>> 0;
    h = Math.imul(h, 0x297a2d39) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
  }
  return h;
}

export const u = (s: number, p: number, k: number) => hash(s, p, k) / 2 ** 32;

export const RANDOM = `
(import rand rand rand-int pick shuffle)
(rand-seed s 7)
(real a (rand))
(real b (rand 2 5))
(int c (rand-int 1 6))
(real|none d (pick (as list[real] {10 20 30})))
(list[int] e (shuffle {1 2 3 4}))
`;

export function bothTimes(expr: (x: string) => string, x: string, type = "real"): [unknown, unknown] {
  const [rt, v] = live(`(real x 0 (>= -1e6) (<= 1e6))
(${type} folded ${expr(x)})
(${type} drawn ${expr("x")})`);
  rt.write(rt.id("x"), null, Number(x));
  return [v("folded"), v("drawn")];
}
