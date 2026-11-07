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

/** free@expr: free, starting at the expression's value when the live model is built. */
export interface StartAttribute {
  type: Type;
  start: Expr;
  deps: [number, string | null][];
  fixed?: true;
}

export type Attribute = FreeAttribute | BoundAttribute | StartAttribute;

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
  /** The declaration's doc@'text', for the illustrator and the author. */
  doc?: string;
  value?: Attribute;
  token?: boolean;
  /** The let name a variable the compiler made holds the value of, read once per change. */
  let?: string;
  // A font's parts read from another font: the part, and that font's id.
  links?: Record<string, number>;
  attrs?: Record<string, Attribute>;
  members?: number[];
  /** A container's clip: a shape in its frame, never drawn, that its members are drawn inside. */
  clip?: number;
  /** A group whose members are measured in screen pixels around its position (mtp-ggs). */
  "fixed-size"?: boolean;
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
  // on-drag: the move's to, which reads the name pointer (mtp-r6al).
  map?: Attribute;
  shape?: number;
  // A formula's LaTeX; a term's name in it and its formula; the formula a display shows, and
  // whether inside a paragraph or as a block (mtp-bz6h).
  tex?: string;
  term?: string;
  formula?: number;
  as?: "inline" | "block";
  // on-view: the canvas it listens to; play: "load", or the view or control it waits for.
  view?: number;
  autoplay?: "load" | number | null;
  // A row or a column: how it places its members (mtp-50n).
  layout?: { axis: "row" | "column"; gap: Attribute; align: Attribute } | null;
  active?: Attribute | null;
  // on-click, on-release, on-dragstart, on-dragend, on-pointermove: whether the event stops at its shape.
  "stop-propagation"?: Attribute | null;
  // canvases: what each shows, in drawing order
  shows?: Shown[];
  transition?: number | null;
}

/** What a canvas shows: a shape's id, or an item that gives a shape, none or a list of them. */
export type Shown = number | Attribute;

/** A canvas's items that give what it shows, in order: the k-th is what shownBy(k) is about. */
export function itemsOf(view: Obj): Attribute[] {
  return (view.shows ?? []).filter((s): s is Attribute => typeof s !== "number");
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
  // Attribute values every shape of one kind has, by kind or instance:motif, left out of those
  // shapes (mtpc.md, "Shared attribute values").
  shared?: Record<string, Record<string, Attribute>>;
  // Each structured type, written once; where a type is written, a number is its position here
  // (mtpc.md, "Top level").
  "type-table"?: Type[];
}

export const FORMAT_VERSION = 4;

export function isBound(p: Attribute): p is BoundAttribute {
  return "bound" in p;
}

export function isStart(p: Attribute): p is StartAttribute {
  return "start" in p;
}
