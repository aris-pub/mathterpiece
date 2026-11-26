// What the conformance tests of docs/spec/evaluation.md share.
import { Runtime } from "../../../src/runtime.ts";
import { compile, live } from "../compile.ts";

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

/** The text of a real literal of x: a number written with no point or exponent is an int. */
export function real(x: number): string {
  const text = String(x);
  return /[.e]/.test(text) ? text : `${text}.0`;
}

/**
 * For each expression of X and value of X: the value folded with X written as that value, and the
 * value that the runtime computes once it writes that value to a variable. All are compiled in one
 * source, since each compile runs the mtp command.
 */
export function bothTimesMany(cases: [string, number][], type = "real|none"): [unknown, unknown][] {
  const source = cases
    .map(
      ([expr, x], i) => `(real x${i} 0 (>= -1e6) (<= 1e6))
(${type} folded${i} ${expr.replaceAll("X", real(x))})
(${type} drawn${i} ${expr.replaceAll("X", `x${i}`)})`,
    )
    .join("\n");
  const [rt, v] = live(source);
  return cases.map(([, x], i) => {
    rt.write(rt.id(`x${i}`), null, x);
    return [v(`folded${i}`), v(`drawn${i}`)];
  });
}

/** x clamped to the number limit, as a real. */
export const clamp = (x: number) => Math.max(-1e150, Math.min(1e150, x));

/** x rounded to a number of places, halves away from zero, on its shortest decimal form. */
export function rounded(x: number, places: number): string {
  const [mantissa, exponent = "0"] = String(Math.abs(x)).split("e");
  const [whole, fraction = ""] = mantissa!.split(".");
  const digits = BigInt(whole! + fraction);
  // |x| is digits times 10^(exponent - fraction.length), and the result is n / 10^places.
  const shift = places - (fraction.length - Number(exponent));
  let n: bigint;
  if (shift >= 0) n = digits * 10n ** BigInt(shift);
  else {
    const d = 10n ** BigInt(-shift);
    n = digits / d + ((digits % d) * 2n >= d ? 1n : 0n);
  }
  const text = n.toString().padStart(places + 1, "0");
  const sign = x < 0 && n !== 0n ? "-" : "";
  return sign + (places ? `${text.slice(0, -places)}.${text.slice(-places)}` : text);
}

/** The number of digits after the point in the shortest decimal form of x. */
export function decimalPlaces(x: number): number {
  const [mantissa, exponent = "0"] = String(x).split("e");
  return Math.max((mantissa!.split(".")[1] ?? "").length - Number(exponent), 0);
}

// Every random function reads free variables, so that a test can write its arguments.
export const RANDOM_FREE = `
(import rand rand rand-int pick shuffle)
(rand-seed s 7)
(real lo 2) (real hi 5)
(int ilo 1) (int ihi 6)
(list[real] xs {10 20 30})
(real a (rand))
(real b (rand lo hi))
(int c (rand-int ilo ihi))
(real|none d (pick xs))
(list[real] e (shuffle xs))
`;

/** The live model of a source, a reader of its values, and the site of each random variable. */
export function randomLive(source: string) {
  const doc = compile(source);
  const rt = new Runtime(doc);
  const sites = new Map<string, number>();
  for (const o of doc.objects as { name: string; value?: { bound?: unknown[] } }[]) {
    const bound = o.value?.bound;
    if (bound && ["rand", "rand-int", "pick", "shuffle"].includes(bound[0] as string)) {
      sites.set(o.name, bound[2] as number);
    }
  }
  return { rt, v: (name: string) => rt.value(rt.id(name), null), site: (name: string) => sites.get(name)! };
}
