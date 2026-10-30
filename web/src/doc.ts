// The JSON the compiler writes (format version 1). Expressions are arrays whose first element is
// an operation name; a plain array of numbers is a point; anything else is a plain value.

export type Expr = unknown;

export interface Obj {
  id: number;
  kind: string;
  name: string | null;
  parent?: number;
  attrs: Record<string, Expr>;
  members?: number[];
  // motif
  motif?: string;
  params?: Record<string, Expr>;
  // hidden value
  type?: string;
  frame?: number | null;
  // canvas: what it shows, in drawing order
  shows?: number[];
  // state
  conditions?: Expr[];
  moves?: [number, string, Expr][] | null;
  // controls; a toggle with no target (null) holds its own value
  target?: [number, string] | null;
  state?: number;
  states?: number[];
  start?: number | null;
  steps?: unknown[][];
  // on-drag
  node?: number;
  // on-drag: when it is attached; canvas: when each thing it shows is shown (null: always)
  when?: Expr;
}

export interface Fn {
  params: [string, unknown][];
  body: Expr;
}

export interface Doc {
  mtp: number;
  objects: Obj[];
  functions: Record<string, Fn>;
  names: Record<string, number>;
  depends: Record<string, string[]>;
}
