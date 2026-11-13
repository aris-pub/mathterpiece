// Whether two values are the same for reading a play's or a stepper's step from the scene, and a
// canvas's rest (the author, 2026-11-12 and 2026-11-13): reals within about a millionth of their
// size, points and lists when each of their numbers is, and bools, strings and choices exactly. A
// color is kept as #rrggbbaa, whole numbers, so it is the same only when written the same.
const TOLERANCE = 1e-6;
// Below this a difference is rounding, whatever the size of the values.
const FLOOR = 1e-12;

export function same(a: unknown, b: unknown): boolean {
  if (typeof a === "number" && typeof b === "number") {
    const d = Math.abs(a - b);
    return a === b || d <= FLOOR || d <= TOLERANCE * Math.max(Math.abs(a), Math.abs(b));
  }
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((x, i) => same(x, b[i]));
  return a === b;
}
