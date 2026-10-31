// Evaluates a JSON document: values by object id and attribute, and what writes change. A port
// of the Python backend's Runtime, which reads the same JSON.
import type { Doc, Expr, Obj } from "./doc.ts";
import { Token, mixCss, needsCss } from "./colors.ts";
import { format, pyStr } from "./format.ts";
import { IDENTITY, Matrix, compose, translate } from "./matrix.ts";
import { COMPARISONS, Complex, MtpError, STDLIB, abs, fold, mod, power } from "./stdlib.ts";

export const RECURSION_LIMIT = 1000;

// The other ways of reading a shape, and which of them are positions.
const PROPERTIES: Record<string, Set<string>> = {
  rect: new Set(["center", "size", "from", "to"]),
  ellipse: new Set(["center", "size"]),
  line: new Set(["from", "to"]),
  triangle: new Set(["center", "r"]),
};
const POINTS = new Set(["center", "from", "to"]);
// Objects whose expressions read positions in scene coordinates.
const CONTROLS = new Set(["slider", "button", "play", "toggle", "animation", "on-drag", "on-click"]);
const ARITHMETIC = new Set(["+", "-", "*", "/"]);

/** An object passed as a value, as in (dist a b). */
class Ref {
  constructor(readonly id: number) {}
}

/** Several values from a group attribute, spread into the call around them. */
class Splice {
  constructor(readonly values: unknown[]) {}
}

type Env = Record<string, unknown>;

export class Runtime {
  readonly objects: Obj[];
  private cache = new Map<string, unknown>();
  private active = new Set<string>();
  private written = new Map<string, unknown>();
  private frames = new Map<number, Matrix>();
  private depth = 0;
  /** Texts in the middle of changing: the old text, and how far the change has gone (0 to 1). */
  morphs = new Map<number, [string, number]>();

  /**
   * resolve gives what the page makes of a CSS value for a property (a token, or a mix; colors
   * as #rrggbbaa), or null without a page; a token then is its default.
   */
  constructor(
    readonly doc: Doc,
    private rng: () => number = Math.random,
    private resolve: (css: string, property: string) => string | null = () => null,
  ) {
    this.objects = doc.objects;
  }

  /** Forgets everything computed, for when the page may have restyled the color tokens. */
  refresh(): void {
    this.cache.clear();
    this.frames.clear();
  }

  /** A token's or a mix's color as the page makes it; any other value as it is. */
  resolved(value: unknown): unknown {
    if (value instanceof Token) return this.resolve(value.css, value.property) ?? value.fallback;
    if (needsCss(value)) return this.resolve(value, "color") ?? value;
    return value;
  }

  // A token's value, which may be computed, as the default its CSS variable falls back to: another
  // token falls back through that token's own variable.
  private fallback(i: number, attr: string): string {
    const key = `${i}.${attr}`;
    this.active.add(key);
    try {
      const value = this.eval(this.obj(i).attrs[attr], null, {});
      return value instanceof Token ? value.css : String(value);
    } finally {
      this.active.delete(key);
    }
  }

  obj(i: number): Obj {
    const o = this.objects[i];
    if (!o) throw new MtpError(`no object ${i}`);
    return o;
  }

  kind(i: number): string {
    return this.obj(i).kind;
  }

  parent(i: number): number | null {
    return this.obj(i).parent ?? null;
  }

  /** The container whose coordinates object i's expressions read positions in. */
  readingFrame(i: number): number | null {
    const o = this.obj(i);
    if (o.kind === "value") return o.frame ?? null;
    if (o.kind === "state" || CONTROLS.has(o.kind)) return null;
    return o.parent ?? null;
  }

  /** A control's write. Everything computed is dropped, since anything might depend on it. */
  write(i: number, attr: string, value: unknown): void {
    if (attr === "pos") {
      const [x, y] = value as number[];
      this.write(i, "x", x);
      this.write(i, "y", y);
      return;
    }
    this.written.set(`${i}.${attr}`, value);
    this.cache.clear();
    this.frames.clear();
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value(i: number, attr: string): any {
    if (attr === "pos") return [this.value(i, "x"), this.value(i, "y")];
    const key = `${i}.${attr}`;
    if (this.written.has(key)) return this.written.get(key);
    if (this.cache.has(key)) return this.cache.get(key);
    if (this.active.has(key)) {
      throw new MtpError(`cycle through ${this.obj(i).name ?? "an anonymous object"}.${attr}`);
    }
    const o = this.obj(i);
    // A toggle on a scene value is that value; a toggle with no target holds its own.
    if (o.kind === "toggle" && attr === "value" && o.target) return this.value(o.target[0], o.target[1]);
    if (o.kind === "color" && attr === "value") {
      const token = new Token(o.name ?? String(i), this.fallback(i, attr));
      this.cache.set(key, token);
      return token;
    }
    if (o.kind === "font" && (attr === "family" || attr === "style" || attr === "weight")) {
      const token = new Token(`${o.name ?? i}-${attr}`, this.fallback(i, attr), `font-${attr}`);
      this.cache.set(key, token);
      return token;
    }
    const raw = o.params && attr in o.params ? o.params[attr] : o.attrs[attr];
    this.active.add(key);
    let result: unknown;
    try {
      result = this.eval(raw, this.readingFrame(i), {});
    } finally {
      this.active.delete(key);
    }
    if (attr === "transform" && Array.isArray(result)) result = Matrix.of(result as number[]);
    this.cache.set(key, result);
    return result;
  }

  /** The items a loop walks: a group's members, or a list's items. */
  private items(value: unknown): unknown[] {
    if (value instanceof Ref) {
      const members = this.obj(value.id).members;
      if (!members) throw new MtpError("a loop walks a group or a list");
      return members.map((m) => new Ref(m));
    }
    return [...(value as unknown[])];
  }

  // Loops over a collection known only while drawing (a group passed to a function).
  private walk(op: string, args: Expr[], frame: number | null, env: Env): unknown {
    if (op === "walk-sort") {
      const [direction, collection, name, key] = args as [string, Expr, string, Expr];
      const items = this.items(this.eval(collection, frame, env));
      const keyed = items.map((item) => [item, this.eval(key, frame, { ...env, [name]: item }) as number] as const);
      const sign = direction === "desc" ? -1 : 1;
      return keyed.sort((a, b) => sign * (a[1] - b[1])).map(([item]) => item);
    }
    if (op === "walk-reduce") {
      const [collection, name, running, start, body] = args as [Expr, string, string, Expr, Expr];
      let value = this.eval(start, frame, env);
      for (const item of this.items(this.eval(collection, frame, env))) {
        value = this.eval(body, frame, { ...env, [name]: item, [running]: value });
      }
      return value;
    }
    const [collection, name, body] = args as [Expr, string, Expr];
    const items = this.items(this.eval(collection, frame, env));
    const each = (item: unknown) => this.eval(body, frame, { ...env, [name]: item });
    if (op === "walk-any") return items.some((item) => Boolean(each(item)));
    if (op === "walk-all") return items.every((item) => Boolean(each(item)));
    return items.map((item) => {
      const v = each(item);
      return typeof v === "boolean" ? v : Number(v);
    });
  }

  eval(e: Expr, frame: number | null, env: Env): unknown {
    if (!Array.isArray(e)) return e;
    if (e.length === 0 || typeof e[0] !== "string") return e;
    const [op, ...args] = e as [string, ...Expr[]];
    if (op.startsWith("walk-")) return this.walk(op, args, frame, env);
    switch (op) {
      case "read": {
        let target = args[0];
        const dynamic = typeof target !== "number";
        if (dynamic) {
          const ref = this.eval(target, frame, env);
          if (!(ref instanceof Ref)) throw new MtpError("expected an object");
          target = ref.id;
        }
        const convert = args.length === 3 || dynamic;
        const into = args.length === 3 ? (args[2] as number | null) : frame;
        return this.read(target as number, args[1] as string, into, convert);
      }
      case "param":
        return this.value(args[0] as number, args[1] as string);
      case "arg":
        return env[args[0] as string];
      case "part": {
        const found = this.eval(args[0], frame, env);
        const base = found instanceof Ref ? this.items(found) : (found as unknown[]);
        const index = typeof args[1] === "number" ? args[1] : Number(this.eval(args[1], frame, env));
        // Negative indexes count from the end, as in the language (and Python).
        const at = index < 0 ? base.length + index : index;
        if (at < 0 || at >= base.length) throw new MtpError(`a list of ${base.length} has no part ${index}`);
        return base[at];
      }
      case "obj":
        return new Ref(args[0] as number);
      case "splice":
        return new Splice(args.map((a) => this.eval(a, frame, env)));
      case "list":
        return args.map((a) => {
          const v = this.eval(a, frame, env);
          return typeof v === "boolean" ? v : Number(v);
        });
      case "complex":
        return new Complex(args[0] as number, args[1] as number);
      case "holds":
        return this.holds(args[0] as number);
      case "inf":
        return Infinity;
      case "-inf":
        return -Infinity;
      case "str":
        return args.map((a) => (typeof a === "string" ? a : this.eval(a, frame, env))).join("");
      case "show": {
        const value = this.resolved(this.eval(args[0], frame, env));
        const kind = args[1] as string;
        const spec = args[2] as string | undefined;
        if (value instanceof Splice) return value.values.map((v) => show(v, kind, spec)).join(" ");
        return show(value, kind, spec);
      }
      case "if":
        return this.eval(this.eval(args[0], frame, env) ? args[1] : args[2], frame, env);
      case "and":
        return args.every((a) => Boolean(this.eval(a, frame, env)));
      case "or":
        return args.some((a) => Boolean(this.eval(a, frame, env)));
      case "not":
        return !this.eval(args[0], frame, env);
      case "cond":
        for (const clause of args as [Expr, Expr][]) {
          if (clause[0] === true || this.eval(clause[0], frame, env)) return this.eval(clause[1], frame, env);
        }
        throw new MtpError("no cond clause held");
      case "let": {
        const inner: Env = { ...env };
        for (const [name, value] of args[0] as [string, Expr][]) inner[name] = this.eval(value, frame, inner);
        return this.eval(args[1], frame, inner);
      }
    }
    const call = op === "call";
    const name = call ? (args[0] as string) : op;
    const values: unknown[] = [];
    for (const a of call ? args.slice(1) : args) {
      const v = this.eval(a, frame, env);
      if (v instanceof Splice) values.push(...v.values);
      else values.push(v);
    }
    if (call && name in this.doc.functions) return this.callFunction(name, values, frame);
    return this.apply(name, values);
  }

  /** Calls an author's function or a built-in one by name, as eases and paths do. */
  invoke(name: string, args: unknown[]): unknown {
    return name in this.doc.functions ? this.callFunction(name, args, null) : this.apply(name, args);
  }

  callFunction(key: string, args: unknown[], frame: number | null): unknown {
    if (this.depth >= RECURSION_LIMIT) {
      throw new MtpError(`recursion is deeper than ${RECURSION_LIMIT} calls`);
    }
    const fn = this.doc.functions[key];
    if (!fn) throw new MtpError(`unknown function ${key}`);
    const env: Env = {};
    fn.params.forEach(([name, fallback], i) => {
      env[name] = i < args.length ? args[i] : fallback;
    });
    this.depth += 1;
    try {
      return this.eval(fn.body, frame, env);
    } finally {
      this.depth -= 1;
    }
  }

  apply(op: string, args: unknown[]): unknown {
    if (ARITHMETIC.has(op)) return fold(op, args);
    if (op === "^") return power(args[0], args[1]);
    if (op === "abs") return abs(args[0]);
    if (op === "mod") return mod(args[0] as number, args[1] as number);
    const compare = COMPARISONS[op];
    if (compare) return compare(this.resolved(args[0]), this.resolved(args[1]));
    if (op === "transform") return compose(...(args as Matrix[]));
    if (op === "mix") return mixCss(args[0], args[1], args[2] as number);
    if (op === "lighten") return mixCss(args[0], "white", args[1] as number);
    if (op === "darken") return mixCss(args[0], "black", args[1] as number);
    if (op === "sort-asc") return [...(args[0] as number[])].sort((a, b) => a - b);
    if (op === "sort-desc") return [...(args[0] as number[])].sort((a, b) => b - a);
    if (op === "reverse") return [...(args[0] as unknown[])].reverse();
    if (op === "any") return (args[0] as boolean[]).some(Boolean);
    if (op === "all") return (args[0] as boolean[]).every(Boolean);
    if (op === "sort-by") {
      const pairs: [unknown, number][] = [];
      for (let k = 1; k < args.length; k += 2) pairs.push([args[k], args[k + 1] as number]);
      const sign = args[0] === "desc" ? -1 : 1;
      return pairs.sort((a, b) => sign * (a[1] - b[1])).map(([member]) => member);
    }
    const fn = STDLIB[op];
    if (fn) return fn(this.rng, ...args.map((a) => (a instanceof Ref ? this.point(a.id) : a)));
    throw new MtpError(`unknown function ${op}`);
  }

  /** attr of object i, in the coordinates of container `into` when converting a position. */
  read(i: number, attr: string, into: number | null, convert: boolean): unknown {
    const here = this.parent(i);
    if ((attr === "x" || attr === "y") && (!convert || here === into)) return this.value(i, attr);
    const properties = PROPERTIES[this.kind(i)] ?? new Set<string>();
    const positional = attr === "x" || attr === "y" || attr === "pos" || (POINTS.has(attr) && properties.has(attr));
    if (!positional) return properties.has(attr) ? this.property(i, attr) : this.value(i, attr);
    let point =
      attr === "x" || attr === "y" || attr === "pos"
        ? [this.value(i, "x"), this.value(i, "y")]
        : (this.property(i, attr) as number[]);
    if (convert) point = this.convert(point, here, into);
    if (attr === "x") return point[0];
    if (attr === "y") return point[1];
    return point;
  }

  convert(point: number[], here: number | null, there: number | null): number[] {
    if (here === there) return point;
    const scene = this.frame(here).apply(point[0] ?? 0, point[1] ?? 0);
    try {
      return this.frame(there).inverse().apply(scene[0], scene[1]);
    } catch (err) {
      throw new MtpError((err as Error).message);
    }
  }

  /** The other ways of reading a shape, computed from what it stores, in its parent's coordinates. */
  property(i: number, name: string): unknown {
    const v = (attr: string) => this.value(i, attr);
    switch (this.kind(i)) {
      case "rect": {
        if (name === "from") return [v("x"), v("y")];
        if (name === "size") return [v("width"), v("height")];
        const share = name === "center" ? 0.5 : 1;
        return [v("x") + share * v("width"), v("y") + share * v("height")];
      }
      case "ellipse":
        return name === "center" ? [v("x"), v("y")] : [2 * v("rx"), 2 * v("ry")];
      case "line": {
        const end = name === "from" ? [v("x1"), v("y1")] : [v("x2"), v("y2")];
        return [v("x") + end[0], v("y") + end[1]];
      }
      default: {
        const corners = [v("a"), v("b"), v("c")] as number[][];
        const mid = [0, 1].map((k) => corners.reduce((s, p) => s + (p[k] ?? 0), 0) / 3) as [number, number];
        if (name === "center") return [v("x") + mid[0], v("y") + mid[1]];
        const a = corners[0] ?? [0, 0];
        return Math.hypot((a[0] ?? 0) - mid[0], (a[1] ?? 0) - mid[1]);
      }
    }
  }

  /** Maps a container's members' coordinates to scene coordinates. */
  frame(container: number | null): Matrix {
    if (container === null) return IDENTITY;
    let m = this.frames.get(container);
    if (!m) {
      let local = this.value(container, "transform") as Matrix;
      if (this.kind(container) === "motif") {
        local = translate(this.value(container, "x"), this.value(container, "y")).times(local);
      }
      m = this.frame(this.parent(container)).times(local);
      this.frames.set(container, m);
    }
    return m;
  }

  point(i: number): number[] {
    return this.frame(this.parent(i)).apply(this.value(i, "x"), this.value(i, "y"));
  }

  /** Places a shape drawn around the origin: its transform, its x and y, then its parents. */
  shape(i: number): Matrix {
    const at = translate(this.value(i, "x"), this.value(i, "y"));
    return this.frame(this.parent(i)).times(at).times(this.value(i, "transform") as Matrix);
  }

  /** Opacity multiplies down the tree of motifs, unlike the other style attributes. */
  opacity(i: number): number {
    let result = this.value(i, "opacity") as number;
    for (let p = this.parent(i); p !== null; p = this.parent(p)) {
      if (this.kind(p) === "motif") result *= this.value(p, "opacity") as number;
    }
    return result;
  }

  /** Whether all of a state's conditions hold; = on numbers allows a small tolerance. */
  holds(state: number): boolean {
    for (const cond of this.obj(state).conditions ?? []) {
      if (Array.isArray(cond) && cond[0] === "=" && cond.length === 3) {
        const a = this.resolved(this.eval(cond[1], null, {}));
        const b = this.resolved(this.eval(cond[2], null, {}));
        if (!close(a, b)) return false;
      } else if (!this.eval(cond, null, {})) {
        return false;
      }
    }
    return true;
  }
}

function close(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((x, i) => close(x, b[i]));
  if (typeof a === "number" && typeof b === "number") {
    return Math.abs(a - b) <= Math.max(1e-9 * Math.max(Math.abs(a), Math.abs(b)), 1e-12);
  }
  return a === b;
}

/** A value shown in a string: by its format spec, or Python's default. */
export function show(value: unknown, kind: string, spec?: string): string {
  if (spec) {
    if (typeof value === "number" && kind === "int") return format(Math.round(value), spec, "int");
    return format(value, spec, typeof value === "string" ? "str" : kind === "int" ? "int" : "real");
  }
  if (typeof value === "number") return kind === "int" ? String(Math.round(value)) : pyStr(value);
  if (typeof value === "boolean") return value ? "True" : "False";
  if (Array.isArray(value)) return `(${value.map((v) => pyStr(Number(v))).join(", ")})`;
  if (value instanceof Complex) return complexStr(value);
  return String(value);
}

function complexStr(z: Complex): string {
  const part = (x: number) => (Number.isInteger(x) ? String(x) : pyStr(x));
  if (z.re === 0 && !Object.is(z.re, -0)) return `${part(z.im)}j`;
  const sign = z.im < 0 || Object.is(z.im, -0) ? "-" : "+";
  return `(${part(z.re)}${sign}${part(Math.abs(z.im))}j)`;
}
