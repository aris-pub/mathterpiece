// How a variable or an attribute moves along a transition: the ease turns progress into how far along the move is,
// and the path (a straight line by default) gives the value there (docs/reference.md,
// "Transitions and animations").
import { mix } from "./builtins.ts";
import type { FnValue } from "./runtime.ts";

/** An ease as a move carries it (docs/mtpc.md, "Steps"). */
export type Ease = string | ["step", number] | ["step-ease", number] | { func: number };

export const EASES: Record<string, (t: number) => number> = {
  linear: (t) => t,
  "ease-in": (t) => t * t * t,
  "ease-out": (t) => 1 - (1 - t) ** 3,
  "ease-in-out": (t) => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2),
};

/** How far along a move is at progress p in [0, 1]. */
export function applyEase(ease: Ease, p: number, fn: (id: number) => FnValue): number {
  if (typeof ease === "string") return EASES[ease]!(p);
  if (Array.isArray(ease)) {
    const [kind, n] = ease;
    // Each jump of (step n) comes at the start of its interval.
    if (kind === "step") return p >= 1 ? 1 : Math.min(Math.floor(p * n) + 1, n) / n;
    return p >= n ? 1 : 0;
  }
  return Number(fn(ease.func)([p], null));
}

/** What kind of value is moved, for how it moves when no path is given. */
export type Moves = "number" | "point" | "color" | "jump";

/** The value u of the way from a to b along a straight line. */
export function along(from: unknown, to: unknown, u: number, moves: Moves): unknown {
  // Exactly the end at 1, whatever rounding would give. A number or a point goes past its ends
  // when the ease does, as a spring overshoots; a color or a jump stops at them.
  if (u === 1) return to;
  if (moves === "jump") return u >= 1 ? to : from;
  if (moves === "color") {
    if (u >= 1) return to;
    // none is mixed as transparent (type-system.md 5.c).
    return mix((from as string | null) ?? "#00000000", (to as string | null) ?? "#00000000", Math.max(u, 0));
  }
  if (moves === "point") return (from as number[]).map((x, i) => x + ((to as number[])[i]! - x) * u);
  return (from as number) + ((to as number) - (from as number)) * u;
}
