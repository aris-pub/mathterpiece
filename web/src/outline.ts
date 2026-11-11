// A shape's outline as pieces of geometry, and the part of it a pen has drawn so far (mtp-ggsb;
// docs/reference.md, "The scene and shapes"). Each outline starts where SVG starts the element
// the shape is drawn as, and runs the same way, so the dashes of a part drawn are those of the
// whole outline.
import { inner, sweep } from "./arc.ts";
import { curveAt } from "./curve.ts";

type Point = number[];

/** A straight piece, a piece of an axis-aligned ellipse from angle `from` turning `turn`
 * degrees (the angle of the circle it is stretched from), or a Bézier curve through its points. */
export type Piece =
  | { line: [Point, Point] }
  | { arc: { cx: number; cy: number; rx: number; ry: number; from: number; turn: number } }
  | { bezier: Point[] };

/** An outline: one or more runs of pieces, each run drawn by its own pen, all at once. */
export type Outline = Piece[][];

const rad = (deg: number) => (deg * Math.PI) / 180;

function onEllipse(a: { cx: number; cy: number; rx: number; ry: number }, deg: number): Point {
  return [a.cx + a.rx * Math.cos(rad(deg)), a.cy + a.ry * Math.sin(rad(deg))];
}

const arc = (cx: number, cy: number, rx: number, ry: number, from: number, turn: number): Piece => ({
  arc: { cx, cy, rx, ry, from, turn },
});

function through(points: Point[]): Piece[] {
  return points.slice(1).map((p, k): Piece => ({ line: [points[k]!, p] }));
}

/** The outline of a shape of kind `kind`, from its attributes, in its own frame. */
export function outlineOf(kind: string, v: (attr: string) => unknown): Outline {
  const n = (attr: string) => v(attr) as number;
  switch (kind) {
    case "circle":
      return n("r") > 0 ? [[arc(n("x"), n("y"), n("r"), n("r"), 0, 360)]] : [];
    case "ellipse":
      return n("rx") > 0 && n("ry") > 0 ? [[arc(n("x"), n("y"), n("rx"), n("ry"), 0, 360)]] : [];
    case "rect":
      return [rect(n("x") - n("width") / 2, n("y") - n("height") / 2, n("width"), n("height"), n("rx"), n("ry"))].filter(
        (run) => run.length > 0,
      );
    case "line":
      return [[{ line: [v("from") as Point, v("to") as Point] }]];
    case "triangle": {
      const [a, b, c] = ["a", "b", "c"].map((k) => v(k) as Point);
      return [through([a!, b!, c!, a!])];
    }
    case "polyline":
    case "polygon": {
      const points = v("points") as Point[];
      if (points.length < 2) return [];
      return [through(kind === "polygon" ? [...points, points[0]!] : points)];
    }
    case "curve":
      return [[{ bezier: [v("from") as Point, ...(v("controls") as Point[]), v("to") as Point] }]];
    case "arc": {
      const s = sweep(n("from"), n("to"));
      return s !== 0 && n("r") > 0 ? [[arc(n("x"), n("y"), n("r"), n("r"), n("from"), s)]] : [];
    }
    case "ring":
      return ring(n("x"), n("y"), n("r"), n("width"), n("from"), n("to"));
    default:
      return [];
  }
}

// As SVG draws a rect: from the end of the first rounded corner along the bottom edge, which in
// the scene's coordinates, y pointing up, is counterclockwise. A corner is rounded only when rx
// and ry are both above 0, and by no more than half the side.
function rect(x: number, y: number, w: number, h: number, rx0: number, ry0: number): Piece[] {
  if (w <= 0 || h <= 0) return [];
  const round = rx0 > 0 && ry0 > 0;
  const rx = round ? Math.min(rx0, w / 2) : 0;
  const ry = round ? Math.min(ry0, h / 2) : 0;
  const run: Piece[] = [];
  const side = (a: Point, b: Point) => {
    if (a[0] !== b[0] || a[1] !== b[1]) run.push({ line: [a, b] });
  };
  const corner = (cx: number, cy: number, from: number) => {
    if (round) run.push(arc(cx, cy, rx, ry, from, 90));
  };
  side([x + rx, y], [x + w - rx, y]);
  corner(x + w - rx, y + ry, -90);
  side([x + w, y + ry], [x + w, y + h - ry]);
  corner(x + w - rx, y + h - ry, 0);
  side([x + w - rx, y + h], [x + rx, y + h]);
  corner(x + rx, y + h - ry, 90);
  side([x, y + h - ry], [x, y + ry]);
  corner(x + rx, y + ry, 180);
  return run;
}

// A whole ring is two circles, each drawn as a circle from the ring's from; a part of one is one
// run along its edges, in the order SVG draws it.
function ring(cx: number, cy: number, r: number, width: number, from: number, to: number): Outline {
  const s = sweep(from, to);
  if (s === 0 || r <= 0) return [];
  const ri = inner(r, width);
  const outer = arc(cx, cy, r, r, from, s);
  if (Math.abs(s) === 360) return ri > 0 ? [[outer], [arc(cx, cy, ri, ri, from, s)]] : [[outer]];
  const start = onEllipse({ cx, cy, rx: r, ry: r }, from);
  const end = onEllipse({ cx, cy, rx: r, ry: r }, from + s);
  if (ri === 0) return [[outer, { line: [end, [cx, cy]] }, { line: [[cx, cy], start] }]];
  const back = arc(cx, cy, ri, ri, from + s, -s);
  const innerEnd = onEllipse({ cx, cy, rx: ri, ry: ri }, from);
  return [[outer, { line: [end, onEllipse({ cx, cy, rx: ri, ry: ri }, from + s)] }, back, { line: [innerEnd, start] }]];
}

// How finely an ellipse or a curve is measured: its length to this many points along it.
const SAMPLES = 256;

// Each piece's length from its start to SAMPLES + 1 points along it, at equal steps of its own
// parameter; a circle's and a line's are exact without them.
function table(at: (u: number) => Point): number[] {
  const out = [0];
  let prev = at(0);
  for (let k = 1; k <= SAMPLES; k++) {
    const p = at(k / SAMPLES);
    out.push(out[k - 1]! + Math.hypot(p[0]! - prev[0]!, p[1]! - prev[1]!));
    prev = p;
  }
  return out;
}

function sampled(piece: Piece): ((u: number) => Point) | null {
  if ("bezier" in piece) return (u) => curveAt(piece.bezier, u);
  if ("arc" in piece && piece.arc.rx !== piece.arc.ry) {
    const a = piece.arc;
    return (u) => onEllipse(a, a.from + a.turn * u);
  }
  return null;
}

function lengthOf(piece: Piece): number {
  if ("line" in piece) {
    const [a, b] = piece.line;
    return Math.hypot(b[0]! - a[0]!, b[1]! - a[1]!);
  }
  const at = sampled(piece);
  if (at) return table(at)[SAMPLES]!;
  const a = (piece as { arc: { rx: number; turn: number } }).arc;
  return a.rx * Math.abs(rad(a.turn));
}

// The parameter, from 0 to 1, at which a measured piece has the given share of its length.
function parameterAt(lengths: number[], share: number): number {
  const want = share * lengths[SAMPLES]!;
  let k = 1;
  while (k < SAMPLES && lengths[k]! < want) k++;
  const [lo, hi] = [lengths[k - 1]!, lengths[k]!];
  return (k - 1 + (hi > lo ? (want - lo) / (hi - lo) : 0)) / SAMPLES;
}

// The piece from its start to the given share of its length.
function cut(piece: Piece, share: number): Piece {
  if ("line" in piece) {
    const [a, b] = piece.line;
    return { line: [a, [a[0]! + share * (b[0]! - a[0]!), a[1]! + share * (b[1]! - a[1]!)]] };
  }
  const at = sampled(piece);
  const u = at ? parameterAt(table(at), share) : share;
  if ("arc" in piece) return { arc: { ...piece.arc, turn: piece.arc.turn * u } };
  return { bezier: split(piece.bezier, u) };
}

// De Casteljau's construction: the control points of a curve from its start to t.
function split(points: Point[], t: number): Point[] {
  const out = [points[0]!];
  let level = points;
  while (level.length > 1) {
    level = level.slice(1).map((q, k) => [0, 1].map((d) => (1 - t) * level[k]![d]! + t * q[d]!));
    out.push(level[0]!);
  }
  return out;
}

/** The runs of an outline from their starts to the given share of each one's length. */
export function drawnPart(outline: Outline, share: number): Outline {
  return outline.map((run) => {
    const lengths = run.map(lengthOf);
    let left = share * lengths.reduce((a, b) => a + b, 0);
    const out: Piece[] = [];
    for (let k = 0; k < run.length && left > 0; k++) {
      const length = lengths[k]!;
      out.push(left >= length ? run[k]! : cut(run[k]!, left / length));
      left -= length;
    }
    if (out.length === 0 && run.length > 0) out.push(cut(run[0]!, 0));
    return out;
  });
}

// Rounded so that a point on an axis is written as 0, not as 1.2e-16 or -0, as arc.ts does.
const num = (x: number) => {
  const r = Math.round(x * 1e9) / 1e9;
  return r === 0 ? "0" : String(r);
};
const point = (p: Point) => `${num(p[0]!)},${num(p[1]!)}`;

function startOf(piece: Piece): Point {
  if ("line" in piece) return piece.line[0];
  if ("bezier" in piece) return piece.bezier[0]!;
  return onEllipse(piece.arc, piece.arc.from);
}

/** An outline as an SVG path. An SVG arc cannot end where it starts, so a piece of an ellipse
 * turning more than half a turn is written in two halves, as arc.ts writes an arc. */
export function outlinePath(outline: Outline): string {
  let d = "";
  for (const run of outline) {
    if (run.length === 0) continue;
    d += `M${point(startOf(run[0]!))}`;
    for (const piece of run) {
      if ("line" in piece) d += `L${point(piece.line[1])}`;
      else if ("bezier" in piece) {
        const rest = piece.bezier.slice(1);
        d += `${rest.length === 2 ? "Q" : "C"}${rest.map(point).join(" ")}`;
      } else {
        const a = piece.arc;
        const halves = Math.abs(a.turn) > 180 ? 2 : 1;
        const flag = a.turn > 0 ? 1 : 0;
        for (let k = 1; k <= halves; k++) {
          d += `A${num(a.rx)},${num(a.ry)},0,0,${flag},${point(onEllipse(a, a.from + (a.turn * k) / halves))}`;
        }
      }
    }
  }
  return d;
}
