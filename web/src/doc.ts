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

export interface FreePlace {
  type: Type;
  free: unknown;
  fixed?: true;
}

export interface BoundPlace {
  type: Type;
  bound: Expr;
  deps: [number, string | null][];
  fixed?: true;
}

export type Place = FreePlace | BoundPlace;

export interface Clamp {
  place: [number, string | null];
  op: ">=" | ">" | "<=" | "<";
  limit: Place;
}

export type Step =
  | ["move", [number, string | null], number, number, unknown]
  | ["wait", number]
  | ["at-once" | "in-order", ...Step[]];

export interface Obj {
  kind: string;
  type: Type;
  access: "scene" | "page";
  name: string | null;
  value?: Place;
  token?: boolean;
  attrs?: Record<string, Place>;
  members?: number[];
  of?: string;
  // transitions
  from?: Place | null;
  to?: Place | null;
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
  when?: Place | null | [Place, number[]][];
  transition?: number | null;
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

export function isBound(p: Place): p is BoundPlace {
  return "bound" in p;
}
