// The standard library and arithmetic, following the Python backend's semantics.
import { sameColor } from "./colors.ts";
import { Matrix } from "./matrix.ts";

export class Complex {
  constructor(
    readonly re: number,
    readonly im: number,
  ) {}
}

export type Point = readonly number[];

export class MtpError extends Error {}

type Num = number | Complex;

function complex(x: Num): Complex {
  return x instanceof Complex ? x : new Complex(x, 0);
}

function add(a: unknown, b: unknown): unknown {
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, i) => x + (b[i] as number));
  if (a instanceof Complex || b instanceof Complex) {
    const x = complex(a as Num);
    const y = complex(b as Num);
    return new Complex(x.re + y.re, x.im + y.im);
  }
  return (a as number) + (b as number);
}

function negate(a: unknown): unknown {
  if (Array.isArray(a)) return a.map((x) => -x);
  if (a instanceof Complex) return new Complex(-a.re, -a.im);
  return -(a as number);
}

function multiply(a: unknown, b: unknown): unknown {
  if (Array.isArray(a)) return a.map((x) => x * (b as number));
  if (Array.isArray(b)) return b.map((y) => (a as number) * y);
  if (a instanceof Complex || b instanceof Complex) {
    const x = complex(a as Num);
    const y = complex(b as Num);
    return new Complex(x.re * y.re - x.im * y.im, x.re * y.im + x.im * y.re);
  }
  return (a as number) * (b as number);
}

function divide(a: unknown, b: unknown): unknown {
  if (b === 0 || (b instanceof Complex && b.re === 0 && b.im === 0)) {
    throw new MtpError("division by zero");
  }
  if (Array.isArray(a)) return a.map((x) => x / (b as number));
  if (a instanceof Complex || b instanceof Complex) {
    const x = complex(a as Num);
    const y = complex(b as Num);
    const d = y.re * y.re + y.im * y.im;
    return new Complex((x.re * y.re + x.im * y.im) / d, (x.im * y.re - x.re * y.im) / d);
  }
  return (a as number) / (b as number);
}

/** + - * / over any number of arguments, left to right, as in the compiler's folding. */
export function fold(op: string, args: unknown[]): unknown {
  if (op === "-" && args.length === 1) return negate(args[0]);
  if (args.length === 0) return op === "+" ? 0 : 1;
  const step = { "+": add, "*": multiply, "/": divide, "-": (a: unknown, b: unknown) => add(a, negate(b)) }[op];
  if (!step) throw new MtpError(`unknown operation ${op}`);
  return args.slice(1).reduce((acc, x) => step(acc, x), args[0]);
}

export function power(base: unknown, exp: unknown): unknown {
  if (base instanceof Complex || exp instanceof Complex) {
    throw new MtpError("^ with complex numbers is not supported here yet");
  }
  const b = base as number;
  const e = exp as number;
  if (b === 0 && e < 0) throw new MtpError("division by zero");
  const result = b ** e;
  if (Number.isNaN(result)) throw new MtpError("the result of ^ is not a real number");
  return result;
}

/** The remainder with the sign of the divisor, like Python's %. */
export function mod(a: number, b: number): number {
  if (b === 0) throw new MtpError("mod by zero");
  const r = a % b;
  return r !== 0 && r < 0 !== b < 0 ? r + b : r;
}

export function abs(x: unknown): number {
  return x instanceof Complex ? Math.hypot(x.re, x.im) : Math.abs(x as number);
}

export function equal(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((x, i) => x === b[i]);
  }
  if (a instanceof Complex || b instanceof Complex) {
    const x = complex(a as Num);
    const y = complex(b as Num);
    return x.re === y.re && x.im === y.im;
  }
  return a === b;
}

export const COMPARISONS: Record<string, (a: unknown, b: unknown) => boolean> = {
  "<": (a, b) => (a as number) < (b as number),
  "<=": (a, b) => (a as number) <= (b as number),
  ">": (a, b) => (a as number) > (b as number),
  ">=": (a, b) => (a as number) >= (b as number),
  "=": equal,
  "!=": (a, b) => !equal(a, b),
  // The compiler writes these when a side is a color, so strings are compared as colors.
  "color=": (a, b) => sameColor(String(a), String(b)),
  "color!=": (a, b) => !sameColor(String(a), String(b)),
};

// math.sin(math.pi) is 1.2e-16, not 0, so right angles in degrees are looked up instead.
const RIGHT_ANGLE_SIN: Record<number, number> = { 0: 0, 90: 1, 180: 0, 270: -1 };

function sind(deg: number): number {
  return RIGHT_ANGLE_SIN[mod(deg, 360)] ?? Math.sin((deg * Math.PI) / 180);
}

function cosd(deg: number): number {
  return sind(deg + 90);
}

function tand(deg: number): number {
  const r = mod(deg, 180);
  if (r === 90) throw new MtpError("tand is undefined at 90 degrees plus a multiple of 180");
  return r === 0 ? 0 : Math.tan((deg * Math.PI) / 180);
}

const degrees = (x: number) => (x * 180) / Math.PI;
const radians = (x: number) => (x * Math.PI) / 180;

function domain(fn: (x: number) => number): (x: number) => number {
  return (x) => {
    const y = fn(x);
    if (Number.isNaN(y)) throw new MtpError("math domain error");
    return y;
  };
}

function lerp(a: unknown, b: unknown, t: number): unknown {
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, i) => x + ((b[i] as number) - x) * t);
  return (a as number) + ((b as number) - (a as number)) * t;
}

function toPolar(p: Point): Point {
  if (p.length !== 2) throw new MtpError("to-polar takes a point of two numbers");
  const [x = 0, y = 0] = p;
  if (x === 0 && y === 0) throw new MtpError("to-polar has no angle at the origin");
  return [Math.hypot(x, y), degrees(Math.atan2(y, x))];
}

function dist(...args: unknown[]): number {
  if (args.length === 4) {
    const [x1, y1, x2, y2] = args as number[];
    return Math.hypot((x2 as number) - (x1 as number), (y2 as number) - (y1 as number));
  }
  const [p, q] = args as [Point, Point];
  if (p.length !== q.length) throw new MtpError("the points given to dist have different sizes");
  return Math.hypot(...p.map((x, i) => x - (q[i] as number)));
}

/** Standard library functions by name. Points arrive as arrays of scene coordinates. */
export const STDLIB: Record<string, (rng: () => number, ...args: unknown[]) => unknown> = {
  dist: (_r, ...a) => dist(...a),
  sqrt: (_r, x) => {
    if ((x as number) < 0) throw new MtpError("sqrt of a negative number");
    return Math.sqrt(x as number);
  },
  max: (_r, ...xs) => Math.max(...(xs as number[])),
  min: (_r, ...xs) => Math.min(...(xs as number[])),
  rand: (rng, a, b) => (a === undefined ? rng() : (a as number) + rng() * ((b as number) - (a as number))),
  rad: (_r, x) => degrees(x as number),
  deg: (_r, x) => x,
  turn: (_r, x) => 360 * (x as number),
  "to-rad": (_r, x) => radians(x as number),
  "to-turn": (_r, x) => (x as number) / 360,
  sin: (_r, x) => Math.sin(x as number),
  cos: (_r, x) => Math.cos(x as number),
  tan: (_r, x) => Math.tan(x as number),
  asin: (_r, x) => domain(Math.asin)(x as number),
  acos: (_r, x) => domain(Math.acos)(x as number),
  atan: (_r, x) => Math.atan(x as number),
  sind: (_r, x) => sind(x as number),
  cosd: (_r, x) => cosd(x as number),
  tand: (_r, x) => tand(x as number),
  asind: (_r, x) => degrees(domain(Math.asin)(x as number)),
  acosd: (_r, x) => degrees(domain(Math.acos)(x as number)),
  atand: (_r, x) => degrees(Math.atan(x as number)),
  lerp: (_r, a, b, t) => lerp(a, b, t as number),
  polar: (_r, r, deg) => [(r as number) * cosd(deg as number), (r as number) * sind(deg as number)],
  "to-polar": (_r, p) => toPolar(p as Point),
  rotate: (_r, deg) => {
    const c = cosd(deg as number);
    const s = sind(deg as number);
    return new Matrix(c, -s, 0, s, c, 0);
  },
  scale: (_r, sx, sy) => new Matrix(sx as number, 0, 0, 0, (sy ?? sx) as number, 0),
  translate: (_r, dx, dy) => new Matrix(1, 0, dx as number, 0, 1, dy as number),
};
