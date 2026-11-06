// Bézier curves (mtp-oya; docs/reference.md, "The scene and shapes"): from one end to the other,
// bent by one control, a quadratic, or two, a cubic.
type Point = number[];

/** The SVG path of the curve from `from` through its controls to `to`. */
export function curvePath(from: Point, controls: Point[], to: Point): string {
  const p = (q: Point) => `${q[0]},${q[1]}`;
  const command = controls.length === 1 ? "Q" : "C";
  return `M${p(from)}${command}${[...controls, to].map(p).join(" ")}`;
}

/** The point at t, from 0 at `from` to 1 at `to`, by de Casteljau's construction. */
export function curveAt(points: Point[], t: number): Point {
  let level = points;
  while (level.length > 1) {
    level = level.slice(1).map((q, k) => [0, 1].map((d) => (1 - t) * level[k]![d]! + t * q[d]!));
  }
  return level[0]!;
}

/** The smallest box around the curve, [x0, y0, x1, y1]: its ends, and each point where it turns
 * back along x or along y. */
export function curveBox(from: Point, controls: Point[], to: Point): number[] {
  const points = [from, ...controls, to];
  const ts = [0, 1];
  for (const d of [0, 1]) ts.push(...turns(points.map((q) => q[d]!)));
  const seen = ts.filter((t) => t >= 0 && t <= 1).map((t) => curveAt(points, t));
  const xs = seen.map((q) => q[0]!);
  const ys = seen.map((q) => q[1]!);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

// Where one coordinate's derivative is 0: a line for a quadratic, a quadratic for a cubic.
function turns(c: number[]): number[] {
  if (c.length === 3) {
    const den = c[0]! - 2 * c[1]! + c[2]!;
    return den === 0 ? [] : [(c[0]! - c[1]!) / den];
  }
  const a = -c[0]! + 3 * c[1]! - 3 * c[2]! + c[3]!;
  const b = 2 * (c[0]! - 2 * c[1]! + c[2]!);
  const k = c[1]! - c[0]!;
  if (Math.abs(a) < 1e-12) return b === 0 ? [] : [-k / b];
  const disc = b * b - 4 * a * k;
  if (disc < 0) return [];
  const r = Math.sqrt(disc);
  return [(-b + r) / (2 * a), (-b - r) / (2 * a)];
}
