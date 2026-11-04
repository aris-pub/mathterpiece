// The geometry of arcs and rings (mtp-5zmn; docs/reference.md, "The scene and shapes"): the SVG
// path each is drawn with, and the box around it. Angles are degrees, counterclockwise.

/** How far an arc or ring turns, from its from to its to: at most one turn either way. */
export function sweep(from: number, to: number): number {
  return Math.max(-360, Math.min(360, to - from));
}

// Rounded so that a point on an axis is written as 0, not as 1.2e-16 or -0.
const num = (x: number) => {
  const r = Math.round(x * 1e9) / 1e9;
  return r === 0 ? "0" : String(r);
};

const at = (cx: number, cy: number, r: number, deg: number) => {
  const t = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
};

const point = (p: number[]) => `${num(p[0]!)},${num(p[1]!)}`;

/** The A commands of an arc from angle a, turning s, with no M. An SVG arc cannot end where it
 * starts, and with ends close together it may take either way round, so an arc of more than half
 * a turn is drawn in two halves. */
function steps(cx: number, cy: number, r: number, a: number, s: number): string {
  const n = Math.abs(s) > 180 ? 2 : 1;
  // In the scene's own coordinates y points up, so counterclockwise is SVG's positive direction.
  const flag = s > 0 ? 1 : 0;
  let out = "";
  for (let k = 1; k <= n; k++) out += `A${num(r)},${num(r)},0,0,${flag},${point(at(cx, cy, r, a + (s * k) / n))}`;
  return out;
}

export function arcPath(cx: number, cy: number, r: number, from: number, to: number): string {
  const s = sweep(from, to);
  if (s === 0) return "";
  return `M${point(at(cx, cy, r, from))}${steps(cx, cy, r, from, s)}`;
}

/** The inner radius of a ring: width in from r, and never past the center. */
export function inner(r: number, width: number): number {
  return r - Math.min(width, r);
}

export function ringPath(cx: number, cy: number, r: number, width: number, from: number, to: number): string {
  const s = sweep(from, to);
  if (s === 0) return "";
  const ri = inner(r, width);
  const outer = `M${point(at(cx, cy, r, from))}${steps(cx, cy, r, from, s)}`;
  if (Math.abs(s) === 360) {
    // Two closed circles, the inner one run the other way, so the hole is not filled and the
    // stroke draws no edge across the band.
    if (ri === 0) return `${outer}Z`;
    return `${outer}ZM${point(at(cx, cy, ri, from))}${steps(cx, cy, ri, from, -s)}Z`;
  }
  const back = ri === 0 ? "" : steps(cx, cy, ri, from + s, -s);
  return `${outer}L${point(at(cx, cy, ri, from + s))}${back}Z`;
}

/** The box around an arc (width null) or a ring, [x0, y0, x1, y1]: its ends, and wherever it
 * crosses one of the four directions along the axes. */
export function arcBox(cx: number, cy: number, r: number, width: number | null, from: number, to: number): number[] | null {
  const s = sweep(from, to);
  if (s === 0) return null;
  const [lo, hi] = s > 0 ? [from, from + s] : [from + s, from];
  const radii = width === null ? [r] : [r, inner(r, width)];
  const pts = radii.flatMap((q) => [at(cx, cy, q, lo), at(cx, cy, q, hi)]);
  for (let k = Math.ceil(lo / 90); k * 90 <= hi; k++) pts.push(at(cx, cy, r, k * 90));
  const xs = pts.map((p) => p[0]!);
  const ys = pts.map((p) => p[1]!);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}
