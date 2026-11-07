// The live model: reads an .mtpc (docs/mtpc.md), turns each expression into a function once,
// and holds the value of every variable and attribute. A write changes a free one and forgets
// only what depends on it; a bound one is computed again the next time it is read (data-model.md, "How reactivity
// works"). The compiler has proved every type, so nothing here checks or converts one.
import { arcBox } from "./arc.ts";
import { curveBox } from "./curve.ts";
import {
  BUILTINS,
  Complex,
  Ref,
  Undefined,
  apply,
  compose,
  equal,
  pointsMean,
  roundHalfAway,
  wrapInto,
} from "./builtins.ts";
import type { Clamp, Doc, Expr, Obj, Attribute, Type } from "./doc.ts";
import { isBound, isStart } from "./doc.ts";
import { cssVariable } from "./css.ts";
import { format, pyStr } from "./format.ts";
import { shuffle, unit } from "./random.ts";

export { cssVariable };

const LIMIT = 1e150;
// What an instance gives its members and reads from them, as a group does.
const SPREAD = new Set([
  "fill",
  "stroke",
  "stroke-width",
  "opacity",
  "fill-opacity",
  "stroke-opacity",
  "dash",
  "dash-offset",
  "line-cap",
  "line-join",
  "pointer-events",
]);
const SHAPES = new Set([
  "circle",
  "rect",
  "ellipse",
  "line",
  "triangle",
  "polyline",
  "polygon",
  "curve",
  "arc",
  "ring",
  "text",
  "group",
  "instance",
]);
// The shapes whose position is the mean of their list of points (mtp-4nt).
const THROUGH_POINTS = new Set(["polyline", "polygon"]);
const CORNERS: Record<string, string[]> = { line: ["from", "to"], triangle: ["a", "b", "c"] };
// A curve's position is the mean of its ends and controls (the author, 2026-11-06).
const fromPoints = (kind: string) => CORNERS[kind] !== undefined || THROUGH_POINTS.has(kind) || kind === "curve";
// Attributes that are points in their shape's frame, which a read converts.
const POINT_ATTRS = new Set(["from", "to", "a", "b", "c"]);
// The built-ins that decide something with none themselves; every other one gives none when an
// argument is none (type-system.md 5.c).
const NONE_AWARE = new Set(["or?", "none?", "some?", "somes", "=", "!="]);
const COLLECTIONS = new Set(["map", "where", "sort", "reverse", "reduce", "sum", "count", "any", "all"]);

/** What an expression needs to run: the names around it, and the frame of its caller. */
interface Ctx {
  locals: Record<string, unknown>;
  frame: number | null;
}

type Compiled = (ctx: Ctx) => unknown;
type CompiledCss = (ctx: Ctx) => string | null;
/** A function value: its arguments, and the frame of the expression calling it. */
export type FnValue = (args: unknown[], frame: number | null) => unknown;

const TOP: Ctx = { locals: {}, frame: null };


function key(id: number, attr: string | null): string {
  return `${id}:${attr ?? ""}`;
}

// The expression forms, whose second item is always the expression's type (mtpc.md).
const OPS = new Set([
  "lit", "list", "format", "read", "obj", "check", "wrap", "local", "call", "apply", "func",
  "builtinfunc", "part", "spread", "if", "and", "or", "anchor", "rand", "builtin",
]);

/** Puts each type written by its position in the file's type table back in its place (mtp-qje3). */
function expandTypes(doc: Doc): void {
  const table = doc["type-table"];
  if (!table) return;
  const at = (t: unknown) => (typeof t === "number" ? table[t] : t);
  const walk = (x: unknown): void => {
    if (Array.isArray(x)) {
      if (x.length >= 2 && typeof x[0] === "string" && OPS.has(x[0])) x[1] = at(x[1]);
      for (const v of x) walk(v);
    } else if (x && typeof x === "object") {
      const o = x as Record<string, unknown>;
      for (const key of ["type", "result", "base"]) if (key in o) o[key] = at(o[key]);
      // A type's constraints hold no expression, and ["wrap", lo, hi] is not one.
      for (const [key, v] of Object.entries(o)) if (key !== "constraints") walk(v);
    }
  };
  for (const part of [doc.types, doc.objects, doc.functions, doc.shared]) walk(part);
  delete doc["type-table"];
}

export class Runtime {
  readonly doc: Doc;
  readonly objects: Obj[];
  /** How many bound values have been computed, so a test can see what a write recomputes. */
  evaluations = 0;
  private parents: (number | null)[];
  private free = new Map<string, unknown>();
  private bound = new Map<string, Compiled>();
  // free@ values whose starts are not read yet: each is read once, when the model is built.
  private starts = new Map<string, Compiled>();
  private css_ = new Map<string, CompiledCss | null>();
  // The rows and columns whose members are being measured, so are not moved to their places.
  private unplaced = new Set<number>();
  private types = new Map<string, Type>();
  private cache = new Map<string, unknown>();
  private dependents = new Map<string, Set<string>>();
  private functions: Compiled[] = [];
  private listeners: ((changed: Set<string>) => void)[] = [];
  // Each row's and column's places, as placesIn last worked them out.
  private places = new Map<number, Map<number, number[]>>();
  // While writes are made together, what they changed, told to the listeners once at the end.
  private pending: Set<string> | null = null;
  // The named types the file declares (type-system.md 5.a), by name.
  private named = new Map<string, Type>();

  constructor(doc: Doc) {
    this.doc = doc;
    expandTypes(doc);
    // Each shape gets back the values its kind shares, each a copy, as it was before the file
    // wrote them once (mtp-jru8).
    for (const o of doc.objects) {
      const table = o.attrs && doc.shared?.[o.kind === "instance" ? `instance:${o.of}` : o.kind];
      if (!table) continue;
      for (const [attr, p] of Object.entries(table)) if (!(attr in o.attrs!)) o.attrs![attr] = structuredClone(p);
    }
    this.objects = doc.objects;
    for (const d of doc.types as { name: string; kind: string; type?: Type }[]) {
      if (d.kind === "type") this.named.set(d.name, d.type!);
    }
    this.parents = doc.objects.map(() => null);
    doc.objects.forEach((o, i) => {
      for (const m of o.members ?? []) this.parents[m] = i;
      if (o.clip !== undefined) this.parents[o.clip] = i;
    });
    this.functions = doc.functions.map((f) => this.compile(f.body));
    doc.objects.forEach((o, i) => {
      if (o.value) this.load(i, null, o.value);
      for (const [attr, p] of Object.entries(o.attrs ?? {})) this.load(i, attr, p);
    });
    // While a shape does not exist every read of it, and of its members when it is a container,
    // is none, so each of their attributes follows its exists-when (mtp-b9g0).
    doc.objects.forEach((o, i) => {
      if (!o.attrs?.exists) return;
      const ek = key(i, "exists");
      if (!this.dependents.has(ek)) this.dependents.set(ek, new Set());
      const follow = (j: number) => {
        for (const attr of Object.keys(this.objects[j]!.attrs ?? {})) {
          if (j !== i || attr !== "exists") this.dependents.get(ek)!.add(key(j, attr));
        }
        for (const m of this.objects[j]!.members ?? []) follow(m);
      };
      follow(i);
    });
    // A start may read another, which is then read first.
    for (const k of [...this.starts.keys()]) if (this.starts.has(k)) this.started(k);
  }

  private started(k: string): unknown {
    const fn = this.starts.get(k)!;
    this.starts.delete(k);
    const v = fn(TOP);
    this.free.set(k, v);
    return v;
  }

  private resolve(t: Type): Type {
    while (typeof t === "object" && "named" in t && this.named.has(t.named)) t = this.named.get(t.named)!;
    return t;
  }

  /** A type with its name, broadening and narrowing taken off: what its values are. */
  core(t: Type): Type {
    t = this.resolve(t);
    while (typeof t === "object" && ("union" in t || "refine" in t)) {
      t = this.resolve("union" in t ? t.union[0] : t.refine);
    }
    return t;
  }

  private constraints(t: Type): [string, ...unknown[]][] {
    t = this.resolve(t);
    while (typeof t === "object" && "union" in t) t = this.resolve(t.union[0]);
    if (typeof t !== "object" || !("refine" in t)) return [];
    return [...this.constraints(t.refine), ...t.constraints];
  }

  private load(id: number, attr: string | null, p: Attribute): void {
    const k = key(id, attr);
    this.types.set(k, p.type);
    if (isStart(p)) {
      this.starts.set(k, this.compile(p.start));
    } else if (isBound(p)) {
      this.bound.set(k, this.compile(p.bound));
      for (const [d, a] of p.deps) {
        const dk = key(d, a);
        if (!this.dependents.has(dk)) this.dependents.set(dk, new Set());
        this.dependents.get(dk)!.add(k);
      }
    } else {
      this.free.set(k, this.decode(p.type, p.free));
    }
  }

  /** Called with the variables and attributes that may have changed after every write. */
  onChange(listener: (changed: Set<string>) => void): void {
    this.listeners.push(listener);
  }

  /** Whether a shape exists now: not while its exists-when, or a container's around it, does
   * not hold. */
  exists(id: number): boolean {
    for (let i: number | null = id; i !== null; i = this.parent(i)) {
      if (this.has(i, "exists") && !this.get(key(i, "exists"))) return false;
    }
    return true;
  }

  /** The id of a named object. */
  id(name: string): number {
    const i = this.doc.names[name];
    if (i === undefined) throw new Error(`no object named ${name}`);
    return i;
  }

  /** A variable's or an attribute's value as stored, in its shape's own frame; pos is x and y. */
  value(id: number, attr: string | null = null): unknown {
    const o = this.objects[id]!;
    if (attr !== "exists" && !this.exists(id)) return null;
    if (attr === null && o.kind !== "variable") return new Ref(id);
    if (attr === "pos" && !this.has(id, "pos")) {
      if (fromPoints(o.kind)) return this.mean(id, null);
      return [this.value(id, "x"), this.value(id, "y")];
    }
    if ((attr === "x" || attr === "y") && fromPoints(o.kind) && !this.has(id, attr)) {
      return (this.mean(id, null) as number[])[attr === "x" ? 0 : 1];
    }
    return this.get(key(id, attr));
  }

  private has(id: number, attr: string | null): boolean {
    const k = key(id, attr);
    return this.free.has(k) || this.bound.has(k) || this.starts.has(k);
  }

  private get(k: string): unknown {
    if (this.free.has(k)) return this.free.get(k);
    if (this.starts.has(k)) return this.started(k);
    if (this.cache.has(k)) return this.cache.get(k);
    const fn = this.bound.get(k);
    if (!fn) throw new Error(`no variable or attribute ${k}`);
    this.evaluations++;
    const v = fn(TOP);
    this.cache.set(k, v);
    return v;
  }

  /** The container an object sits in: a group, an instance or the scene; null for globals. */
  parent(id: number): number | null {
    return this.parents[id] ?? null;
  }

  /**
   * The transform from a shape's frame to its container's: an instance's x and y (when
   * members), then its translate, then its transform (reference.md, "Coordinates"). The members
   * of a fixed-size group are in screen pixels: pixel is how many scene units one pixel is on
   * the canvas drawing them. Anything else that reads them, which no canvas sizes, sees them all
   * at the group's position, its box of no size (mtp-ggs).
   */
  local(id: number, members = false, pixel = 0): number[] {
    const o = this.objects[id]!;
    const steps: number[][] = [];
    if (members && o["fixed-size"]) steps.push([pixel, 0, 0, pixel, 0, 0]);
    if (o.kind === "instance" && members) {
      steps.push([1, 0, 0, 1, this.value(id, "x") as number, this.value(id, "y") as number]);
    }
    if (this.has(id, "translate")) {
      const [tx, ty] = this.value(id, "translate") as number[];
      steps.push([1, 0, 0, 1, tx!, ty!]);
    }
    if (this.has(id, "transform")) steps.push(this.value(id, "transform") as number[]);
    // A member of a row or a column is moved last to its place after the members before it.
    const row = this.parents[id];
    if (row !== null && row !== undefined && this.objects[row]!.layout && !this.unplaced.has(row)) {
      const [dx, dy] = this.placesIn(row).get(id) ?? [0, 0];
      steps.push([1, 0, 0, 1, dx!, dy!]);
    }
    return compose(...steps);
  }

  /**
   * Where a row's or a column's members are moved to (mtp-50n): the first that exists stays
   * where it is; each next one goes a gap after the box of the one before, along the row (or down
   * the column), lined up with the first by the edge align names. A member that does not exist
   * takes no space.
   */
  private placesIn(row: number): Map<number, number[]> {
    // Each box below reads the places of the rows inside it, so with layouts inside layouts the
    // work multiplies; places stay as they are until something is written.
    const known = this.places.get(row);
    if (known) return known;
    const o = this.objects[row]!;
    const layout = o.layout!;
    const gap = this.evaluate(layout.gap) as number;
    const align = this.evaluate(layout.align) as string;
    const out = new Map<number, number[]>();
    // The members' boxes as they would be with no place given yet.
    this.unplaced.add(row);
    try {
      let first: number[] | null = null;
      let last: number[] | null = null;
      for (const m of o.members ?? []) {
        const b = this.box(m, row);
        if (b === null) continue;
        if (first === null || last === null) {
          first = last = b;
          continue;
        }
        const across = (lo: number, hi: number) =>
          align === "middle"
            ? (first![lo]! + first![hi]!) / 2 - (b[lo]! + b[hi]!) / 2
            : align === "bottom" || align === "left"
              ? first![lo]! - b[lo]!
              : first![hi]! - b[hi]!;
        const dx: number = layout.axis === "row" ? last[2]! + gap - b[0]! : across(0, 2);
        const dy: number = layout.axis === "row" ? across(1, 3) : last[1]! - gap - b[3]!;
        out.set(m, [dx, dy]);
        last = [b[0]! + dx, b[1]! + dy, b[2]! + dx, b[3]! + dy];
      }
    } finally {
      this.unplaced.delete(row);
    }
    this.places.set(row, out);
    return out;
  }

  /** The transform from the frame a container's members live in to the scene's. */
  toScene(container: number | null): number[] {
    const steps: number[][] = [];
    for (let j = container; j !== null; j = this.parents[j]!) {
      if (this.objects[j]!.kind === "scene") break;
      steps.push(this.local(j, true));
    }
    return compose(...steps);
  }

  /** The type of a variable or an attribute. */
  typeOf(id: number, attr: string | null): Type | undefined {
    return this.types.get(key(id, attr));
  }

  /**
   * Writes a free variable or attribute (a shape's pos writes its x and y; a group's attribute,
   * and an instance's fill, stroke and so on, each member's), brought into its type's constraints
   * first (type-system.md 5.b). Gives whether anything changed.
   */
  write(id: number, attr: string | null, value: unknown): boolean {
    const changed = new Set<string>();
    this.writeInto(id, attr, value, changed);
    if (changed.size === 0) return false;
    if (this.pending) for (const k of changed) this.pending.add(k);
    else for (const l of this.listeners) l(changed);
    return true;
  }

  /**
   * Runs work whose writes the listeners hear of once, at the end, as one change: a drag that
   * tries many values must not redraw the page for each.
   */
  together<T>(work: () => T): T {
    if (this.pending) return work();
    const changed = (this.pending = new Set<string>());
    try {
      return work();
    } finally {
      this.pending = null;
      if (changed.size > 0) for (const l of this.listeners) l(changed);
    }
  }

  private writeInto(id: number, attr: string | null, value: unknown, changed: Set<string>): void {
    const o = this.objects[id]!;
    // A group's or an instance's attribute that is not its own is each member's (mtp-4cw5).
    if ((o.kind === "group" || o.kind === "instance") && attr !== null && !this.has(id, attr)) {
      if (attr !== "pos" || o.kind === "group") {
        for (const m of o.members ?? []) this.writeInto(m, attr, value, changed);
        return;
      }
    }
    if ((THROUGH_POINTS.has(o.kind) || o.kind === "curve") && (attr === "x" || attr === "y")) {
      const [mx, my] = this.mean(id, null) as number[];
      return this.writeInto(id, "pos", attr === "x" ? [value, my] : [mx, value], changed);
    }
    if (attr === "pos" && !this.has(id, "pos")) {
      const [x, y] = value as number[];
      if (THROUGH_POINTS.has(o.kind)) {
        // A polyline's position moves every point together.
        const [mx, my] = this.mean(id, null) as number[];
        const points = this.value(id, "points") as number[][];
        this.writeKey(key(id, "points"), points.map(([px, py]) => [px! + x! - mx!, py! + y! - my!]), changed);
        return;
      }
      if (o.kind === "curve") {
        // A curve's position moves its ends and its controls together.
        const [mx, my] = this.mean(id, null) as number[];
        const by = ([px, py]: number[]) => [px! + x! - mx!, py! + y! - my!];
        for (const c of ["from", "to"]) this.writeKey(key(id, c), by(this.value(id, c) as number[]), changed);
        this.writeKey(key(id, "controls"), (this.value(id, "controls") as number[][]).map(by), changed);
        return;
      }
      if (CORNERS[o.kind]) {
        // A line's or triangle's position moves every end or corner together.
        const [mx, my] = this.mean(id, null) as number[];
        for (const c of CORNERS[o.kind]!) {
          const [cx, cy] = this.value(id, c) as number[];
          this.writeKey(key(id, c), [cx! + x! - mx!, cy! + y! - my!], changed);
        }
        return;
      }
      this.writeKey(key(id, "x"), x, changed);
      this.writeKey(key(id, "y"), y, changed);
      return;
    }
    this.writeKey(key(id, attr), value, changed);
  }

  private writeKey(k: string, value: unknown, changed: Set<string>): void {
    if (!this.free.has(k)) throw new Error(`${k} is not a free variable or attribute`);
    const t = this.types.get(k)!;
    const old = this.free.get(k);
    const v = this.constrain(t, value, old);
    // A write that changes nothing is skipped, so nothing downstream is computed again.
    if (v === undefined || equal(v, old)) return;
    this.free.set(k, v);
    changed.add(k);
    this.places.clear();
    this.forget(k, changed);
  }

  private forget(k: string, changed: Set<string>): void {
    for (const d of this.dependents.get(k) ?? []) {
      if (!this.cache.has(d) && changed.has(d)) continue;
      this.cache.delete(d);
      changed.add(d);
      this.forget(d, changed);
    }
  }

  /**
   * A write brought into a type: a range clamps (a strict bound that is broken skips the
   * write), an int rounds, a choice holds its last valid value, and every number stays within
   * ±10^150. undefined means the write is skipped.
   */
  private constrain(t: Type, value: unknown, old: unknown): unknown {
    if (value === null) return value;
    const base = this.core(t);
    let v = value;
    if (typeof v === "number") {
      v = Math.min(Math.max(v, -LIMIT), LIMIT);
      // Rounded first, so an int that wraps never rounds up out of its interval.
      if (base === "int") v = roundHalfAway(v as number);
      for (const [op, limit, top] of this.constraints(t)) {
        if (op === "wrap") v = wrapInto(v as number, limit as number, top as number);
        const lim = limit as number;
        if (op === ">=" && (v as number) < lim) v = lim;
        if (op === "<=" && (v as number) > lim) v = lim;
        if ((op === ">" && (v as number) <= lim) || (op === "<" && (v as number) >= lim)) return undefined;
      }
      if (base === "int") v = roundHalfAway(v as number);
    }
    for (const [op, choices] of this.constraints(t)) {
      if (op === "one-of" && !(choices as unknown[]).includes(v)) return old;
      if (op === "const") return undefined;
    }
    return v;
  }

  /** A writer's clamp: the value its condition allows for this write. */
  clamp(c: Clamp, value: number): number {
    const lim = this.evaluate(c.limit) as number;
    if (c.op === ">=" || c.op === ">") return Math.max(value, lim);
    return Math.min(value, lim);
  }

  /**
   * A color variable or attribute as CSS, when it is computed from tokens: through each token's
   * CSS variable, so the page's CSS restyles it too (docs/mtpc.md, "Objects"). null when it reads
   * no token, or reads one only where this does not follow it (inside a function's body or a
   * let), and is then drawn with its value.
   */
  css(id: number, attr: string | null): string | null {
    const f = this.cssOf(id, attr);
    return f ? f(TOP) : null;
  }

  private cssOf(id: number, attr: string | null): CompiledCss | null {
    const k = key(id, attr);
    if (this.css_.has(k)) return this.css_.get(k)!;
    const o = this.objects[id]!;
    let f: CompiledCss | null = null;
    if (attr === null && o.kind === "variable" && o.token) {
      f = () => {
        const v = this.value(id, null);
        return v === null ? null : `var(${cssVariable(o.name!)}, ${String(v)})`;
      };
    } else {
      const p = attr === null ? o.value : o.attrs?.[attr];
      if (p && isBound(p)) f = this.compileCss(p.bound as Expr);
    }
    this.css_.set(k, f);
    return f;
  }

  // A color expression as CSS, or null when no token reaches it through the parts followed.
  private compileCss(e: Expr): CompiledCss | null {
    const [op] = e;
    const parts = e.slice(2);
    // A part that reads no token is drawn with its value.
    const either = (part: Expr): CompiledCss => {
      const css = this.compileCss(part);
      if (css) return css;
      const f = this.compile(part);
      return (ctx) => {
        const v = f(ctx);
        return v === null ? null : String(v);
      };
    };
    switch (op) {
      case "read":
        return this.cssOf(parts[0] as number, parts[1] as string | null);
      case "part": {
        // A member read through a variable or parameter that holds a namespace stays its
        // token, as a read of it by its own name does (mtp-ateh).
        const [whole, attr] = parts as [Expr, unknown];
        if (typeof attr !== "string") return null;
        const [of, plain] = [this.compile(whole), this.compile(e)];
        return (ctx) => {
          const g = of(ctx);
          if (g instanceof Ref && this.objects[g.id]!.kind === "namespace") {
            const css = this.cssOf(this.member(g.id, attr), null);
            if (css) return css(ctx);
          }
          const v = plain(ctx);
          return v === null ? null : String(v);
        };
      }
      case "check":
        return this.compileCss(parts[0] as Expr);
      case "if": {
        const [c, a, b] = parts as Expr[];
        if (!this.compileCss(a!) && !this.compileCss(b!)) return null;
        const [test, fa, fb] = [this.compile(c!), either(a!), either(b!)];
        return (ctx) => (test(ctx) ? fa(ctx) : fb(ctx));
      }
      case "cond": {
        const clauses = parts[0] as [Expr, Expr][];
        const otherwise = parts[1] as Expr;
        if (!clauses.some(([, v]) => this.compileCss(v)) && !this.compileCss(otherwise)) return null;
        const tests = clauses.map(([c, v]) => [this.compile(c), either(v)] as const);
        const last = either(otherwise);
        return (ctx) => {
          for (const [c, v] of tests) if (c(ctx)) return v(ctx);
          return last(ctx);
        };
      }
      case "builtin": {
        const [name, ...args] = parts as [string, ...Expr[]];
        const toward: Record<string, Expr> = {
          lighten: ["lit", "color", "#ffffffff"],
          darken: ["lit", "color", "#000000ff"],
        };
        if (name !== "mix" && !(name in toward)) return null;
        const [a, b, t] = name === "mix" ? args : [args[0]!, toward[name]!, args[1]!];
        if (!this.compileCss(a!) && !this.compileCss(b!)) return null;
        const [fa, fb, ft] = [either(a!), either(b!), this.compile(t!)];
        return (ctx) => {
          const [ca, cb, w] = [fa(ctx), fb(ctx), ft(ctx) as number];
          if (ca === null || cb === null || w === null) return null;
          return `color-mix(in srgb, ${ca} ${percent(1 - w)}, ${cb} ${percent(w)})`;
        };
      }
      default:
        return null;
    }
  }

  /** The value of a condition, a limit or a when, which belong to no attribute. */
  evaluate(p: Attribute): unknown {
    if (isStart(p)) return this.compile(p.start)(TOP);
    if (!isBound(p)) return this.decode(p.type, p.free);
    this.evaluations++;
    return this.compile(p.bound)(TOP);
  }

  // Values ------------------------------------------------------------------------------

  /** A value as the .mtpc writes it, read by its type (mtpc.md, "Values"). */
  decode(t: Type, v: unknown): unknown {
    if (v === null || v === undefined) return null;
    const c = this.core(t);
    // JSON has no infinity, so the .mtpc writes a real that is infinite as a name.
    if (c === "real" && v === "infty") return Number.POSITIVE_INFINITY;
    if (c === "real" && v === "-infty") return Number.NEGATIVE_INFINITY;
    if (c === "ratio") {
      const [num, den] = v as [number, number];
      return num / den;
    }
    if (c === "complex") {
      const [re, im] = v as [number, number];
      return new Complex(re, im);
    }
    if (typeof c === "object" && "list" in c) return (v as unknown[]).map((x) => this.decode(c.list, x));
    if (typeof v === "object" && !Array.isArray(v)) {
      const o = v as Record<string, unknown>;
      if ("ref" in o) return new Ref(o.ref as number);
      if ("func" in o) return this.functionValue(o.func as number, {});
      if ("builtin" in o) return builtinValue(o.builtin as string);
    }
    return v;
  }

  // Expressions -------------------------------------------------------------------------

  /** An expression as one function, made once, when the file loads. */
  compile(e: Expr): Compiled {
    const [op, t] = e;
    const parts = e.slice(2);
    switch (op) {
      case "lit": {
        const v = this.decode(t, parts[0]);
        return () => v;
      }
      case "list": {
        const items = (parts as Expr[]).map((p) => this.compile(p));
        // A point with a coordinate that is none is none (type-system.md, "Where it comes from").
        if (this.core(t) === "point") {
          return (ctx) => {
            const xy = items.map((f) => f(ctx));
            return xy.includes(null) ? null : xy;
          };
        }
        return (ctx) => items.map((f) => f(ctx));
      }
      case "format":
        return this.compileFormat(parts);
      case "read": {
        const [id, attr, frame] = parts as [number, string | null, number | null | "caller"];
        return (ctx) => this.read(id, attr, frame === "caller" ? ctx.frame : frame);
      }
      case "obj": {
        const ref = new Ref(parts[0] as number);
        return () => ref;
      }
      case "wrap": {
        const inner = this.compile(parts[0] as Expr);
        const [lo, hi] = [parts[1] as number, parts[2] as number];
        return (ctx) => {
          const v = inner(ctx);
          return v === null ? null : wrapInto(v as number, lo, hi);
        };
      }
      case "check": {
        const inner = this.compile(parts[0] as Expr);
        const cs = parts[1] as [string, number][];
        return (ctx) => {
          const v = inner(ctx);
          return v === null || cs.every(([o, lim]) => holds(o, v as number, lim)) ? v : null;
        };
      }
      case "local": {
        const name = parts[0] as string;
        return (ctx) => ctx.locals[name];
      }
      case "call": {
        const fid = parts[0] as number;
        const args = (parts.slice(1) as Expr[]).map((p) => this.compile(p));
        const params = this.doc.functions[fid]!.params;
        return (ctx) => this.call(fid, params, args.map((f) => f(ctx)), ctx.frame);
      }
      case "apply": {
        const f = this.compile(parts[0] as Expr);
        const args = (parts.slice(1) as Expr[]).map((p) => this.compile(p));
        return (ctx) => (f(ctx) as FnValue)(args.map((a) => a(ctx)), ctx.frame);
      }
      case "func": {
        const fid = parts[0] as number;
        const captured = parts[1] as string[];
        return (ctx) => {
          const around: Record<string, unknown> = {};
          for (const name of captured) around[name] = ctx.locals[name];
          return this.functionValue(fid, around);
        };
      }
      case "builtinfunc": {
        const f = builtinValue(parts[0] as string);
        return () => f;
      }
      case "part":
        return this.compilePart(parts);
      case "spread": {
        const whole = this.compile(parts[0] as Expr);
        const attr = parts[1] as string;
        return (ctx) => {
          const g = whole(ctx) as Ref;
          return (this.objects[g.id]!.members ?? []).map((m) => this.attrOf(m, attr, ctx.frame));
        };
      }
      case "if": {
        const [c, a, b] = (parts as Expr[]).map((p) => this.compile(p)) as [Compiled, Compiled, Compiled];
        return (ctx) => (c(ctx) ? a(ctx) : b(ctx));
      }
      case "cond": {
        const clauses = (parts[0] as [Expr, Expr][]).map(([c, v]) => [this.compile(c), this.compile(v)]);
        const otherwise = this.compile(parts[1] as Expr);
        return (ctx) => {
          for (const [c, v] of clauses) if (c!(ctx)) return v!(ctx);
          return otherwise(ctx);
        };
      }
      case "and":
      case "or": {
        const items = (parts as Expr[]).map((p) => this.compile(p));
        const stop = op === "or";
        return (ctx) => {
          for (const f of items) if (Boolean(f(ctx)) === stop) return stop;
          return !stop;
        };
      }
      case "let": {
        const bindings = (parts[0] as [string, Expr][]).map(([n, x]) => [n, this.compile(x)] as const);
        const body = this.compile(parts[1] as Expr);
        return (ctx) => {
          const locals = { ...ctx.locals };
          for (const [n, f] of bindings) locals[n] = f({ ...ctx, locals });
          return body({ ...ctx, locals });
        };
      }
      case "rand":
      case "rand-int":
      case "pick":
      case "shuffle": {
        // The place it is written, the seed it follows, then its arguments (mtp-bjn0).
        const site = parts[0] as number;
        const seed = this.compile(parts[1] as Expr);
        const args = (parts.slice(2) as Expr[]).map((p) => this.compile(p));
        return (ctx) => {
          const s = seed(ctx) as number;
          const vs = args.map((f) => f(ctx));
          if (op === "shuffle") return shuffle(vs[0] as unknown[], s, site);
          const u = unit(s, site);
          if (op === "pick") {
            const xs = vs[0] as unknown[];
            return xs.length ? xs[Math.floor(u * xs.length)] : null;
          }
          const [lo, hi] = vs.length ? (vs as number[]) : [0, 1];
          if (op === "rand-int") return lo! + Math.floor(u * (hi! - lo! + 1));
          return lo! + u * (hi! - lo!);
        };
      }
      case "anchor": {
        const [side, target, gap, frame] = parts as [string, Expr, Expr, number | null | "caller"];
        const shape = this.compile(target);
        const by = this.compile(gap);
        return (ctx) => {
          const ref = shape(ctx) as Ref | null;
          const box = ref === null ? null : this.box(ref.id, frame === "caller" ? ctx.frame : frame);
          return box === null ? null : anchorOf(side, box, by(ctx) as number);
        };
      }
      case "builtin":
        return this.compileBuiltin(t, parts);
      default:
        throw new Error(`unknown expression ${op}`);
    }
  }

  private compileFormat(parts: unknown[]): Compiled {
    const pieces = parts.map((p) => {
      if (typeof p === "string") return () => p;
      const [e, spec] = p as [Expr, string];
      const f = this.compile(e);
      const t = this.core(e[1]);
      return (ctx: Ctx) => {
        const v = f(ctx);
        return v === null ? null : show(v, t, spec);
      };
    });
    return (ctx) => {
      let out = "";
      for (const piece of pieces) {
        const s = piece(ctx);
        // A string with a part that is none is none.
        if (s === null) return null;
        out += s;
      }
      return out;
    };
  }

  private compilePart(parts: unknown[]): Compiled {
    const whole = this.compile(parts[0] as Expr);
    const k = parts[1];
    if (typeof k === "string") return (ctx) => this.partOf(whole(ctx), k, ctx.frame);
    const index = this.compile(k as Expr);
    return (ctx) => {
      const w = whole(ctx);
      const i = index(ctx);
      if (w === null) return null;
      if (w instanceof Ref) {
        const members = this.objects[w.id]!.members ?? [];
        if (typeof i === "string") {
          const m = members.find((x) => this.objects[x]!.name === i);
          return m === undefined ? null : new Ref(m);
        }
        const m = members.at(i as number);
        return m === undefined ? null : new Ref(m);
      }
      const items = w as unknown[];
      const n = i as number;
      return n >= -items.length && n < items.length ? items.at(n) : null;
    };
  }

  private compileBuiltin(t: Type, parts: unknown[]): Compiled {
    const name = parts[0] as string;
    const args = (parts.slice(1) as Expr[]).map((p) => this.compile(p));
    if (COLLECTIONS.has(name) || name === "somes") return this.compileCollection(name, args);
    if (name === "or?") {
      const [x, d] = args as [Compiled, Compiled];
      return (ctx) => {
        const v = x(ctx);
        return v === null ? d(ctx) : v;
      };
    }
    if (name === "none?" || name === "some?") {
      const [x] = args as [Compiled];
      return (ctx) => (x(ctx) === null) === (name === "none?");
    }
    const impl = BUILTINS[name];
    if (!impl) throw new Error(`unknown built-in ${name}`);
    const aware = NONE_AWARE.has(name);
    const isInt = this.core(t) === "int";
    return (ctx) => {
      const vs = args.map((f) => f(ctx));
      if (!aware && vs.some((v) => v === null)) return null;
      try {
        const v = impl(...vs);
        return isInt && typeof v === "number" ? Math.round(v) : v;
      } catch (err) {
        if (err instanceof Undefined) return null;
        throw err;
      }
    };
  }

  private compileCollection(name: string, args: Compiled[]): Compiled {
    return (ctx) => {
      const vs = args.map((f) => f(ctx));
      if (vs[0] === null) return null;
      const items = this.items(vs[0]);
      const f = vs[vs.length - 1] as FnValue;
      const call = (...a: unknown[]) => f(a, ctx.frame);
      switch (name) {
        case "map":
          return items.map((x) => call(x));
        case "where":
          return items.filter((x) => call(x));
        case "sort": {
          const keys = items.map((x) => call(x) as number);
          return items.map((x, i) => [x, keys[i]!] as const).sort((a, b) => a[1] - b[1]).map(([x]) => x);
        }
        case "reverse":
          return [...items].reverse();
        case "reduce":
          return items.reduce((acc, x) => (f as FnValue)([acc, x], ctx.frame), vs[1]);
        case "sum":
          return items.length === 0 ? 0 : (BUILTINS["+"]!(...items) as number);
        case "count":
          return vs.length === 1 ? items.length : items.filter((x) => call(x)).length;
        case "any":
          return vs.length === 1 ? items.some(Boolean) : items.some((x) => call(x));
        case "all":
          return vs.length === 1 ? items.every(Boolean) : items.every((x) => call(x));
        case "somes":
          return items.filter((x) => x !== null);
        default:
          throw new Error(`unknown collection function ${name}`);
      }
    };
  }

  /** A collection's items: a list's, or a group's or the scene's members. */
  private items(v: unknown): unknown[] {
    if (v instanceof Ref) return (this.objects[v.id]!.members ?? []).map((m) => new Ref(m));
    return v as unknown[];
  }

  /** A function of the file, by id, as a value. */
  fn(fid: number): FnValue {
    return this.functionValue(fid, {});
  }

  private functionValue(fid: number, around: Record<string, unknown>): FnValue {
    const params = this.doc.functions[fid]!.params;
    return (args, frame) => this.call(fid, params, args, frame, around);
  }

  private call(
    fid: number,
    params: { name: string; type: Type }[],
    args: unknown[],
    frame: number | null,
    around: Record<string, unknown> = {},
  ): unknown {
    const locals: Record<string, unknown> = { ...around };
    for (let i = 0; i < params.length; i++) {
      const p = params[i]!;
      // A parameter that does not accept none makes the call none (type-system.md 5.c).
      if (args[i] === null && !acceptsNone(p.type)) return null;
      locals[p.name] = args[i];
    }
    return this.functions[fid]!({ locals, frame });
  }

  // Reads and frames --------------------------------------------------------------------

  /**
   * A variable's or an attribute's value as read from a container: a shape's position converts through every
   * translate and transform that applies to the shape read but not to that container
   * (reference.md, "Coordinates").
   */
  read(id: number, attr: string | null, frame: number | null): unknown {
    const o = this.objects[id]!;
    // A fixed-size group has no position stored: it is where its frame puts its origin.
    if (o["fixed-size"] && attr === "pos") return this.exists(id) ? this.attrOf(id, "pos", frame) : null;
    const v = this.value(id, attr);
    if (attr === null || !SHAPES.has(o.kind) || v === null) return v;
    const isPoint = attr === "pos" || POINT_ATTRS.has(attr);
    const isCoord = attr === "x" || attr === "y";
    if (!isPoint && !isCoord) return v;
    const m = this.frameOf(id, frame);
    if (m === null) return v;
    if (isPoint) return apply(m, v as number[]);
    const p = apply(m, this.value(id, "pos") as number[]);
    return p[attr === "x" ? 0 : 1];
  }

  /**
   * A shape's box as seen from a frame, [left, bottom, right, top], or null when it does not
   * exist: the box around its own geometry's corners after every transform on the way, and a
   * container's, the box around its members' that exist, cut to its clip's (reference.md,
   * "Placing").
   */
  box(id: number, frame: number | null): number[] | null {
    if (!this.exists(id)) return null;
    const o = this.objects[id]!;
    if (o["fixed-size"]) {
      const [x, y] = this.attrOf(id, "pos", frame) as number[];
      return [x!, y!, x!, y!];
    }
    if (o.kind === "group" || o.kind === "instance") {
      const boxes = (o.members ?? []).map((m) => this.box(m, frame)).filter((b) => b !== null);
      if (boxes.length === 0) return null;
      const around = [0, 1, 2, 3].map((k) => (k < 2 ? Math.min : Math.max)(...boxes.map((b) => b![k]!)));
      const clip = o.clip === undefined ? null : this.box(o.clip, frame);
      if (clip === null) return around;
      // Each side moved into the clip's box: the two boxes' overlap, or, with none, a box of no
      // size at the clip's edge nearest the members.
      return around.map((n, k) => Math.min(Math.max(n, clip[k % 2]!), clip[(k % 2) + 2]!));
    }
    const v = (attr: string) => this.value(id, attr) as number;
    let corners: number[][];
    if (o.kind === "line" || o.kind === "triangle") {
      corners = CORNERS[o.kind]!.map((c) => this.value(id, c) as number[]);
    } else if (THROUGH_POINTS.has(o.kind)) {
      corners = this.value(id, "points") as number[][];
      if (corners.length === 0) return null;
    } else if (o.kind === "curve") {
      const ends = [this.value(id, "from"), this.value(id, "to")] as number[][];
      const controls = this.value(id, "controls") as number[][] | null;
      if (controls === null || ends.some((e) => e === null)) return null;
      const [x0, y0, x1, y1] = curveBox(ends[0]!, controls, ends[1]!) as [number, number, number, number];
      corners = [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
      ];
    } else if (o.kind === "arc" || o.kind === "ring") {
      const own = arcBox(v("x"), v("y"), v("r"), o.kind === "ring" ? v("width") : null, v("from"), v("to"));
      if (own === null) return null;
      const [x0, y0, x1, y1] = own as [number, number, number, number];
      corners = [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
      ];
    } else {
      const [x, y] = [v("x"), v("y")];
      const [hw, hh] =
        o.kind === "circle" ? [v("r"), v("r")] : o.kind === "rect" ? [v("width") / 2, v("height") / 2] : [v("rx"), v("ry")];
      corners = [
        [x - hw, y - hh],
        [x + hw, y - hh],
        [x + hw, y + hh],
        [x - hw, y + hh],
      ];
    }
    if (corners.some((c) => c === null || c.some((n) => n === null || n === undefined))) return null;
    const m = this.frameOf(id, frame);
    const seen = m === null ? corners : corners.map((c) => apply(m, c) as number[]);
    const xs = seen.map((c) => c[0]!);
    const ys = seen.map((c) => c[1]!);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }

  /** The transform from a shape's frame to its container frame's, or null when there is none. */
  private frameOf(id: number, frame: number | null): number[] | null {
    const shared = new Set<number>();
    for (let j: number | null = frame; j !== null; j = this.parents[j]!) shared.add(j);
    const steps: number[][] = [];
    for (let j: number | null = id; j !== null && !shared.has(j); j = this.parents[j]!) {
      if (this.objects[j]!.kind === "scene") break;
      steps.push(this.local(j, j !== id));
    }
    const m = compose(...steps);
    return m.every((x, i) => x === [1, 0, 0, 1, 0, 0][i]) ? null : m;
  }

  /** An attribute of a shape known only while drawing, read from a frame. */
  private attrOf(id: number, attr: string, frame: number | null): unknown {
    const o = this.objects[id]!;
    if (attr === "name") return o.name;
    // A transition's duration is known when compiling and written on it, not as an attribute.
    if (o.kind === "transition" && attr === "duration") return o.duration;
    if (o["fixed-size"] && attr === "pos") {
      const m = this.frameOf(id, frame);
      return m === null ? [0, 0] : apply(m, [0, 0]);
    }
    if (o.kind === "group" && !this.has(id, attr) && attr !== "length" && attr !== "members") {
      return (o.members ?? []).map((m) => this.attrOf(m, attr, frame));
    }
    if (o.kind === "instance" && !this.has(id, attr) && SPREAD.has(attr)) {
      return (o.members ?? []).map((m) => this.attrOf(m, attr, frame));
    }
    if (o.kind === "namespace") {
      // A member is an object of its own, named by the namespace: theme.ink (mtp-4rc).
      const m = this.member(id, attr);
      return this.objects[m]!.kind === "namespace" ? new Ref(m) : this.value(m, null);
    }
    if (attr === "length" && o.members) return o.members.length;
    if (attr === "members") return (o.members ?? []).map((m) => new Ref(m));
    if (o.kind === "instance" && !this.has(id, attr)) {
      const m = (o.members ?? []).find((x) => this.objects[x]!.name === attr);
      if (m !== undefined) return new Ref(m);
    }
    if (fromPoints(o.kind) && (attr === "x" || attr === "y" || attr === "pos")) {
      const p = this.mean(id, frame) as number[];
      return attr === "pos" ? p : p[attr === "x" ? 0 : 1];
    }
    return this.read(id, attr, frame);
  }

  /** The id of a namespace's member, by its own name. */
  member(id: number, attr: string): number {
    const o = this.objects[id]!;
    const m = (o.members ?? []).find((x) => this.objects[x]!.name === `${o.name}.${attr}`);
    if (m === undefined) throw new Error(`${o.name} has no member ${attr}`);
    return m;
  }

  /** The mean of a line's ends, a triangle's corners or a polyline's points: its position. */
  private mean(id: number, frame: number | null): number[] {
    const kind = this.objects[id]!.kind;
    if (THROUGH_POINTS.has(kind) || kind === "curve") {
      const points =
        kind === "curve"
          ? ([this.value(id, "from"), this.value(id, "to"), ...(this.value(id, "controls") as number[][])] as number[][])
          : (this.value(id, "points") as number[][]);
      const own = pointsMean(points);
      // The mean of the points seen from a frame is their mean, moved to that frame.
      const m = frame === null ? null : this.frameOf(id, frame);
      return m === null ? own : (apply(m, own) as number[]);
    }
    const pts = CORNERS[kind]!.map((c) => (frame === null ? this.value(id, c) : this.read(id, c, frame)) as number[]);
    return [0, 1].map((k) => pts.reduce((s, p) => s + p[k]!, 0) / pts.length);
  }

  private partOf(w: unknown, k: string, frame: number | null): unknown {
    if (w === null) return null;
    if (w instanceof Ref) return this.attrOf(w.id, k, frame);
    if (w instanceof Complex) return k === "re" ? w.re : w.im;
    if (Array.isArray(w)) {
      if (k === "length") return w.length;
      return w[k === "x" ? 0 : 1];
    }
    if (typeof w === "string") {
      if (k === "length") return [...w].length;
      const i = "rgba".indexOf(k);
      return Number.parseInt(w.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    }
    return (w as Record<string, unknown>)[k];
  }
}

function holds(op: string, v: number, lim: number): boolean {
  return op === ">=" ? v >= lim : op === ">" ? v > lim : op === "<=" ? v <= lim : v < lim;
}

function acceptsNone(t: Type): boolean {
  return typeof t === "object" && "union" in t;
}

function builtinValue(name: string): FnValue {
  const impl = BUILTINS[name]!;
  return (args) => {
    if (args.some((a) => a === null)) return null;
    try {
      return impl(...args);
    } catch (err) {
      if (err instanceof Undefined) return null;
      throw err;
    }
  };
}

/** A value shown in a string: by its format spec, or as Python shows it with none. */
export function show(v: unknown, t: Type, spec: string): string {
  const kind = typeof t === "string" ? t : "real";
  if (spec) return format(v, spec, kind === "string" || typeof v === "string" ? "str" : kind);
  if (typeof v === "number") return kind === "int" ? String(Math.round(v)) : pyStr(v);
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return `(${v.map((x) => pyStr(Number(x))).join(", ")})`;
  if (v instanceof Complex) return `(${pyStr(v.re)}${v.im < 0 ? "-" : "+"}${pyStr(Math.abs(v.im))}j)`;
  return String(v);
}

function percent(x: number): string {
  return `${Number((100 * x).toFixed(6))}%`;
}

// A point on a box [left, bottom, right, top]: the middle of a side or a corner, pushed out by
// gap on each side it names.
function anchorOf(side: string, box: number[], gap: number): number[] {
  const [l, b, r, t] = box as [number, number, number, number];
  const x = side.includes("left") ? l - gap : side.includes("right") ? r + gap : (l + r) / 2;
  const y = side.startsWith("top") ? t + gap : side.startsWith("bottom") ? b - gap : (b + t) / 2;
  return [x, y];
}
