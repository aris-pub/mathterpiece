// The .mtpc the compiler writes (format version 2; docs/mtpc.md, checked against
// docs/mtpc.schema.json). Expressions are arrays: their operation, their type, then their parts.

export type Type =
  | string
  | { shape: string }
  | { named: string }
  | { component: string }
  | { interface: string; of?: Type }
  | { list: Type }
  | { func: Type[]; result: Type }
  | { union: [Type, "none"] }
  | { refine: Type; constraints: Constraint[] };

export type Constraint = [string, ...unknown[]];

export type Expr = [string, Type, ...unknown[]];

export interface FreeAttribute {
  type: Type;
  free: unknown;
  fixed?: true;
}

export interface BoundAttribute {
  type: Type;
  bound: Expr;
  deps: [number, string | null][];
  fixed?: true;
}

export type Attribute = FreeAttribute | BoundAttribute;

export interface Clamp {
  target: [number, string | null];
  op: ">=" | ">" | "<=" | "<";
  limit: Attribute;
}

export type Step =
  | ["move", [number, string | null], number, number, unknown]
  | ["wait", number]
  | ["at-once" | "in-order", ...Step[]]
  | ["loop", number | null, Step];

export interface Obj {
  kind: string;
  type: Type;
  access: "scene" | "page";
  name: string | null;
  value?: Attribute;
  token?: boolean;
  attrs?: Record<string, Attribute>;
  members?: number[];
  of?: string;
  // transitions
  from?: Attribute | null;
  to?: Attribute | null;
  duration?: number | null;
  ease?: unknown;
  path?: unknown;
  // animations
  steps?: Step;
  // components
  animation?: number | null;
  conditions?: Clamp[];
  target?: [number, string | null] | null;
  shape?: number;
  // on-view: the canvas it listens to; play: "load", or the view or control it waits for.
  view?: number;
  autoplay?: "load" | number | null;
  // A row or a column: how it places its members (mtp-50n).
  layout?: { axis: "row" | "column"; gap: Attribute; align: Attribute } | null;
  when?: Attribute | null;
  // canvases: what each shows, in drawing order
  shows?: Shown[];
  transition?: number | null;
}

/** What a canvas shows: a shape's id, or a when item's condition and shapes. */
export type Shown = number | [Attribute, number[]];

/** A canvas's when items, in order: the k-th is what visible(k) is about. */
export function whenItems(view: Obj): [Attribute, number[]][] {
  return (view.shows ?? []).filter((s): s is [Attribute, number[]] => typeof s !== "number");
}

export interface Param {
  name: string;
  type: Type;
  default?: unknown;
}

export interface Fn {
  params: Param[];
  result: Type;
  body: Expr;
}

export interface Doc {
  mtpc: number;
  types: unknown[];
  objects: Obj[];
  functions: Fn[];
  names: Record<string, number>;
}

export const FORMAT_VERSION = 2;

export function isBound(p: Attribute): p is BoundAttribute {
  return "bound" in p;
}
