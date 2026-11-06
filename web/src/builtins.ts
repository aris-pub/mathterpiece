// The built-in functions (docs/reference.md "Functions" and "Operators"), as the compiler folds
// them (mathterpiece/builtins.py). A built-in called where it is undefined gives none (null):
// the compiler has already proved where that may happen and typed the result to allow it.

export class Complex {
  constructor(
    readonly re: number,
    readonly im: number,
  ) {}
}

/** An object given as a value: a shape, a transition, an animation. */
export class Ref {
  constructor(readonly id: number) {}
}

export type Point = number[];
export type Transform = number[];

/** Raised by a built-in where it is undefined; the caller turns it into none. */
export class Undefined extends Error {}

const MAX_REAL = Number.MAX_VALUE;

function check(ok: boolean): void {
  if (!ok) throw new Undefined();
}

function finite(x: number): number {
  check(Number.isFinite(x) && Math.abs(x) <= MAX_REAL);
  return x;
}

function complex(x: unknown): Complex {
  return x instanceof Complex ? x : new Complex(x as number, 0);
}

function isComplex(...xs: unknown[]): boolean {
  return xs.some((x) => x instanceof Complex);
}

// math.sin(math.pi) is 1.2e-16, not 0, so right angles in degrees are looked up instead.
const RIGHT_ANGLE_SIN: Record<number, number> = { 0: 0, 90: 1, 180: 0, 270: -1 };

export function mod(a: number, b: number): number {
  check(b !== 0);
  return a - b * Math.floor(a / b);
}

export function sind(deg: number): number {
  return RIGHT_ANGLE_SIN[mod(deg, 360)] ?? Math.sin((deg * Math.PI) / 180);
}

export function cosd(deg: number): number {
  return sind(deg + 90);
}

function ratio(a: number, b: number): number {
  check(b !== 0);
  return a / b;
}

function inUnit(x: number): number {
  check(x >= -1 && x <= 1);
  return x;
}

function arc(x: number): number {
  check(Math.abs(x) >= 1);
  return 1 / x;
}

const D = (x: number) => (x * 180) / Math.PI;

function add(a: unknown, b: unknown): unknown {
  if (Array.isArray(a)) return a.map((x, i) => add(x, (b as unknown[])[i]));
  if (isComplex(a, b)) {
    const x = complex(a);
    const y = complex(b);
    return new Complex(x.re + y.re, x.im + y.im);
  }
  return finite((a as number) + (b as number));
}

function negate(a: unknown): unknown {
  if (Array.isArray(a)) return a.map(negate);
  if (a instanceof Complex) return new Complex(-a.re, -a.im);
  return -(a as number);
}

function multiply(a: unknown, b: unknown): unknown {
  // A number times a point or a list multiplies each item.
  if (Array.isArray(a) && !Array.isArray(b)) return a.map((x) => multiply(x, b));
  if (Array.isArray(b) && !Array.isArray(a)) return b.map((x) => multiply(a, x));
  if (Array.isArray(a)) return a.map((x, i) => multiply(x, (b as unknown[])[i]));
  if (isComplex(a, b)) {
    const x = complex(a);
    const y = complex(b);
    return new Complex(x.re * y.re - x.im * y.im, x.re * y.im + x.im * y.re);
  }
  return finite((a as number) * (b as number));
}

function divide(a: unknown, b: unknown): unknown {
  if (isComplex(a, b)) {
    const x = complex(a);
    const y = complex(b);
    const d = y.re * y.re + y.im * y.im;
    check(d !== 0);
    return new Complex((x.re * y.re + x.im * y.im) / d, (x.im * y.re - x.re * y.im) / d);
  }
  return finite(ratio(a as number, b as number));
}

function power(a: unknown, b: unknown): unknown {
  if (isComplex(a, b)) {
    const x = complex(a);
    const y = complex(b);
    const r = Math.hypot(x.re, x.im);
    check(r !== 0 || y.re > 0);
    const theta = Math.atan2(x.im, x.re);
    const lnr = Math.log(r);
    const m = Math.exp(y.re * lnr - y.im * theta);
    const angle = y.im * lnr + y.re * theta;
    return new Complex(m * Math.cos(angle), m * Math.sin(angle));
  }
  const x = a as number;
  const y = b as number;
  check(!(x === 0 && y < 0));
  check(!(x < 0 && !Number.isInteger(y)));
  return finite(x ** y);
}

/** Two values of one type equal: colors as colors, points and lists item by item. */
export function equal(a: unknown, b: unknown): boolean {
  if (a === null || b === null) return a === b;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((x, i) => equal(x, b[i]));
  }
  if (isComplex(a, b)) {
    const x = complex(a);
    const y = complex(b);
    return x.re === y.re && x.im === y.im;
  }
  if (a instanceof Ref && b instanceof Ref) return a.id === b.id;
  if (typeof a === "object" && typeof b === "object") return JSON.stringify(a) === JSON.stringify(b);
  return a === b;
}

/** Halves away from zero, on the number's shortest decimal form (reference.md, "Rounding"). */
export function roundHalfAway(x: number, decimals = 0): number {
  const [mantissa = "0", exp = "0"] = Math.abs(x).toExponential().split("e");
  const digits = mantissa.replace(".", "");
  // digits stand for 0.digits * 10^(e + 1); keep the ones before position e + 1 + decimals.
  const keep = Number(exp) + 1 + decimals;
  if (keep < 0) return x < 0 ? -0 : 0;
  const head = digits.slice(0, keep).padEnd(keep, "0");
  const up = (digits.charCodeAt(keep) || 48) - 48 >= 5;
  const n = BigInt(head || "0") + (up ? 1n : 0n);
  const value = Number(`${n}e${-decimals}`);
  return x < 0 ? -value : value;
}

/** v brought into [lo, hi), for a value whose type wraps (docs/type-system.md, 5.b). */
export function wrapInto(v: number, lo: number, hi: number): number {
  const w = hi - lo;
  const r = (((v - lo) % w) + w) % w;
  // A value just below lo can round up to the whole width.
  return lo + (r >= w ? 0 : r);
}

function lerp(a: unknown, b: unknown, t: number): unknown {
  if (Array.isArray(a)) return a.map((x: number, i) => x + ((b as number[])[i]! - x) * t);
  return (a as number) + ((b as number) - (a as number)) * t;
}

/** Transforms as [a b c d e f]: x' = a x + c y + e, y' = b x + d y + f; the first applies first. */
export function compose(...ts: Transform[]): Transform {
  let [a, b, c, d, e, f] = [1, 0, 0, 1, 0, 0];
  for (const [a2, b2, c2, d2, e2, f2] of ts as [number, number, number, number, number, number][]) {
    [a, b, c, d, e, f] = [
      a2 * a + c2 * b,
      b2 * a + d2 * b,
      a2 * c + c2 * d,
      b2 * c + d2 * d,
      a2 * e + c2 * f + e2,
      b2 * e + d2 * f + f2,
    ];
  }
  return [a, b, c, d, e, f];
}

export function invert(t: Transform): Transform {
  const [a, b, c, d, e, f] = t as [number, number, number, number, number, number];
  const det = a * d - b * c;
  return [d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det];
}

export function apply(t: Transform, [x, y]: Point): Point {
  const [a, b, c, d, e, f] = t as [number, number, number, number, number, number];
  return [a * x! + c * y! + e, b * x! + d * y! + f];
}

function channels(color: string): [number, number, number, number] {
  const n = (k: number) => Number.parseInt(color.slice(k, k + 2), 16);
  return [n(1), n(3), n(5), n(7) / 255];
}

/** t of the way from a to b, as CSS color-mix in sRGB computes it: with premultiplied alpha. */
export function mix(a: string, b: string, t: number): string {
  const ca = channels(a);
  const cb = channels(b);
  const alpha = ca[3] * (1 - t) + cb[3] * t;
  if (alpha === 0) return "#00000000";
  const rgb = [0, 1, 2].map((k) => (ca[k]! * ca[3] * (1 - t) + cb[k]! * cb[3] * t) / alpha);
  const hex = (v: number) => Math.round(v).toString(16).padStart(2, "0");
  return `#${rgb.map(hex).join("")}${hex(alpha * 255)}`;
}

function extreme(pick: (...xs: number[]) => number, args: unknown[]): number {
  const xs = args.flatMap((a) => (Array.isArray(a) ? (a as number[]) : [a as number]));
  check(xs.length > 0);
  return pick(...xs);
}

function log(x: number, base?: number): number {
  check(x > 0);
  if (base === undefined) return Math.log(x);
  check(base > 0 && base !== 1);
  return Math.log(x) / Math.log(base);
}

type Impl = (...args: unknown[]) => unknown;
const n = (f: (x: number) => number): Impl => (x) => finite(f(x as number));

/** Each built-in by its name in the reference. Collections are handled by the runtime. */
// More items than this is undefined: a figure has no use for them, and a page would hang.
const RANGE_LIMIT = 1_000_000;

/**
 * (range start stop (gap g)), stop left out, or (range start stop (num n)), both ends included
 * (mtp-966), as the compiler folds it. Item k is start + k gap, so rounding does not add up.
 */
function range(start: number, stop: number, by: string, step: number): number[] {
  if (by === "num") {
    check(Number.isInteger(step) && step >= 0 && step <= RANGE_LIMIT);
    if (step === 1) return [start];
    return Array.from({ length: step }, (_, k) => (k === step - 1 ? stop : start + (k * (stop - start)) / (step - 1)));
  }
  check(step !== 0);
  const before = (x: number) => (step > 0 ? x < stop : x > stop);
  let n = Math.max(0, Math.ceil((stop - start) / step));
  check(n <= RANGE_LIMIT);
  while (n > 0 && !before(start + (n - 1) * step)) n--;
  while (before(start + n * step)) n++;
  return Array.from({ length: n }, (_, k) => start + k * step);
}

/** The mean of a list of points, [0, 0] for none: a polyline's position (mtp-4nt). */
export function pointsMean(points: number[][]): number[] {
  const n = Math.max(points.length, 1);
  return [0, 1].map((k) => points.reduce((s, p) => s + p[k]!, 0) / n);
}

export const BUILTINS: Record<string, Impl> = {
  "points-mean": (ps) => pointsMean(ps as number[][]),
  range: (start, stop, by, step) => range(start as number, stop as number, by as string, step as number),
  "+": (...xs) => (xs.length === 1 ? xs[0] : xs.reduce(add)),
  "-": (...xs) => (xs.length === 1 ? negate(xs[0]) : xs.reduce((a, b) => add(a, negate(b)))),
  "*": (...xs) => xs.reduce(multiply),
  "/": divide,
  "^": power,
  mod: (a, b) => mod(a as number, b as number),
  abs: (x) => (x instanceof Complex ? Math.hypot(x.re, x.im) : Math.abs(x as number)),
  "=": equal,
  "!=": (a, b) => !equal(a, b),
  "<": (a, b) => (a as number) < (b as number),
  "<=": (a, b) => (a as number) <= (b as number),
  ">": (a, b) => (a as number) > (b as number),
  ">=": (a, b) => (a as number) >= (b as number),
  not: (x) => !x,
  sqrt: (x) => {
    check((x as number) >= 0);
    return Math.sqrt(x as number);
  },
  round: (x, decimals) => roundHalfAway(x as number, (decimals as number | undefined) ?? 0),
  floor: n(Math.floor),
  ceil: n(Math.ceil),
  exp: n(Math.exp),
  log: (x, b) => log(x as number, b as number | undefined),
  min: (...xs) => extreme(Math.min, xs),
  max: (...xs) => extreme(Math.max, xs),
  lerp: (a, b, t) => lerp(a, b, t as number),
  sin: n(Math.sin),
  cos: n(Math.cos),
  tan: n(Math.tan),
  sec: n((x) => ratio(1, Math.cos(x))),
  csc: n((x) => ratio(1, Math.sin(x))),
  cot: n((x) => ratio(Math.cos(x), Math.sin(x))),
  asin: n((x) => Math.asin(inUnit(x))),
  acos: n((x) => Math.acos(inUnit(x))),
  atan: n(Math.atan),
  acot: n((x) => Math.PI / 2 - Math.atan(x)),
  asec: n((x) => Math.acos(arc(x))),
  acsc: n((x) => Math.asin(arc(x))),
  sind: n(sind),
  cosd: n(cosd),
  tand: n((x) => ratio(sind(x), cosd(x))),
  secd: n((x) => ratio(1, cosd(x))),
  cscd: n((x) => ratio(1, sind(x))),
  cotd: n((x) => ratio(cosd(x), sind(x))),
  asind: n((x) => D(Math.asin(inUnit(x)))),
  acosd: n((x) => D(Math.acos(inUnit(x)))),
  atand: n((x) => D(Math.atan(x))),
  acotd: n((x) => 90 - D(Math.atan(x))),
  asecd: n((x) => D(Math.acos(arc(x)))),
  acscd: n((x) => D(Math.asin(arc(x)))),
  rad: n(D),
  turn: n((x) => 360 * x),
  deg: n((x) => x),
  "to-rad": n((x) => (x * Math.PI) / 180),
  "to-turn": n((x) => x / 360),
  polar: (r, a) => [(r as number) * cosd(a as number), (r as number) * sind(a as number)],
  "to-polar": (p) => {
    const [x = 0, y = 0] = p as Point;
    check(x !== 0 || y !== 0);
    return [Math.hypot(x, y), D(Math.atan2(y, x))];
  },
  dist: (p, q) => Math.hypot(...(p as Point).map((x, i) => x - (q as Point)[i]!)),
  rotate: (deg) => {
    const c = cosd(deg as number);
    const s = sind(deg as number);
    return [c, s, -s, c, 0, 0];
  },
  scale: (sx, sy) => [sx, 0, 0, sy ?? sx, 0, 0],
  translate: (dx, dy) => [1, 0, 0, 1, dx, dy],
  transform: (...ts) => compose(...(ts as Transform[])),
  mix: (a, b, t) => mix(a as string, b as string, t as number),
  lighten: (c, t) => mix(c as string, "#ffffffff", t as number),
  darken: (c, t) => mix(c as string, "#000000ff", t as number),
};
