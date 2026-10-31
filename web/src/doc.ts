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
  // canvas: what it shows, in drawing order, and the transition each is shown and hidden with
  // (null: at once)
  shows?: number[];
  transitions?: unknown[];
  // state
  conditions?: Expr[];
  // controls; a toggle with no target (null) holds its own value
  target?: [number, string] | null;
  // controls: the animation they set off; animation: its body
  animation?: number;
  body?: unknown;
  // on-drag and on-click: the node they listen on
  node?: number;
  // on-drag and on-click: when they are attached; canvas: when each thing it shows is shown
  // (null: always)
  when?: Expr;
}

export interface Fn {
  params: [string, unknown][];
  body: Expr;
}

export interface Doc {
  mtp: number;
  // How colors are written: "rgba" (#rrggbbaa) for now.
  colors?: string;
  objects: Obj[];
  functions: Record<string, Fn>;
  names: Record<string, number>;
  depends: Record<string, string[]>;
}
