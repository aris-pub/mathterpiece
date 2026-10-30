// Transitions: pure trajectories through a value's states. A transition goes from a start to an
// end along a path, with an ease deciding how time (or a slider's knob) runs through it. Its
// value at progress p in [0, 1] is path(start, end, ease(p)). Sequences glue their parts end to
// end, each part starting where the one before ended.
import { EASES } from "./animate.ts";
import { mixCss } from "./colors.ts";

export type Ease = string | ["step", number] | ["fn", string];

export type Spec =
  | { kind: "single"; from?: unknown; to?: unknown; duration?: number; ease?: Ease; path?: ["fn", string] }
  | { kind: "wait"; duration: number }
  | { kind: "in-order"; parts: Spec[]; ease?: Ease; defaultDuration?: number; defaultEase?: Ease };

/** How a kind of value moves when no path is given. */
export type ValueKind = "number" | "point" | "color" | "text" | "bool";

/** Calls one of the figure's functions (or the library's) by name. */
export type Call = (name: string, args: unknown[]) => unknown;

/** A text in the middle of changing: the new text, fading in over the old one. */
export interface Crossfade {
  from: string;
  to: string;
  progress: number;
}

// How long each part counts for: its duration in seconds when run by a clock, or its share of
// the track when scrubbed by a slider, where a part without a duration counts as 1.
type Weight = (spec: Spec) => number;

/** The value t seconds after the transition starts from start. */
export function valueAt(spec: Spec, start: unknown, t: number, kind: ValueKind, call: Call): unknown {
  const filled = fill(spec);
  const total = totalDuration(filled);
  const p = total > 0 ? Math.min(Math.max(t / total, 0), 1) : 1;
  return evaluate(filled, start, p, kind, call, clockWeight);
}

/** The value with a slider's knob at u in [0, 1]: durations only share out the track. */
export function valueAtProgress(spec: Spec, start: unknown, u: number, kind: ValueKind, call: Call): unknown {
  return evaluate(fill(spec), start, Math.min(Math.max(u, 0), 1), kind, call, trackWeight);
}

/** How long the transition runs, in seconds. */
export function totalDuration(spec: Spec): number {
  return clockWeight(fill(spec));
}

function clockWeight(spec: Spec): number {
  if (spec.kind === "in-order") return spec.parts.reduce((sum, part) => sum + clockWeight(part), 0);
  if (spec.duration === undefined) throw new Error("a transition needs a duration");
  return spec.duration;
}

function trackWeight(spec: Spec): number {
  if (spec.kind === "in-order") return spec.parts.reduce((sum, part) => sum + trackWeight(part), 0);
  return spec.duration ?? 1;
}

// Default durations and eases pass down to every part without its own, nearest first.
function fill(spec: Spec, duration?: number, ease?: Ease): Spec {
  if (spec.kind === "wait") return spec;
  if (spec.kind === "single") {
    const out = { ...spec };
    if (out.duration === undefined && duration !== undefined) out.duration = duration;
    if (out.ease === undefined && ease !== undefined) out.ease = ease;
    return out;
  }
  const d = spec.defaultDuration ?? duration;
  const e = spec.defaultEase ?? ease;
  return { ...spec, parts: spec.parts.map((part) => fill(part, d, e)) };
}

function evaluate(spec: Spec, start: unknown, p: number, kind: ValueKind, call: Call, weight: Weight): unknown {
  if (spec.kind === "wait") return start;
  if (spec.kind === "single") {
    if (spec.to === undefined) throw new Error("a transition needs an end (to)");
    const from = spec.from === undefined ? start : spec.from;
    const u = applyEase(spec.ease, p, call);
    if (spec.path) return call(spec.path[1], [from, spec.to, u]);
    return along(from, spec.to, u, kind);
  }
  const q = applyEase(spec.ease, p, call);
  const weights = spec.parts.map(weight);
  const total = weights.reduce((sum, w) => sum + w, 0);
  // With no weight at all, every part gets an equal share.
  const shares = total > 0 ? weights : weights.map(() => 1);
  const length = total > 0 ? total : shares.length;
  const place = q * length;
  let value = start;
  let reached = 0;
  for (const [k, part] of spec.parts.entries()) {
    const share = shares[k] ?? 0;
    const last = k === spec.parts.length - 1;
    if (place <= reached + share || last) {
      const local = share > 0 ? Math.min(Math.max((place - reached) / share, 0), 1) : 1;
      return evaluate(part, value, local, kind, call, weight);
    }
    value = endOf(part, value);
    reached += share;
  }
  return value;
}

// Where a part leaves the value, so the next part starts there.
function endOf(spec: Spec, start: unknown): unknown {
  if (spec.kind === "wait") return start;
  if (spec.kind === "single") return spec.to ?? start;
  return spec.parts.reduce((value, part) => endOf(part, value), start);
}

function applyEase(ease: Ease | undefined, p: number, call: Call): number {
  if (ease === undefined) return p;
  if (typeof ease === "string") return (EASES[ease] ?? EASES.linear!)(p);
  if (ease[0] === "step") return p >= ease[1] ? 1 : 0;
  return Number(call(ease[1], [p]));
}

// The default path for each kind of value.
function along(from: unknown, to: unknown, u: number, kind: ValueKind): unknown {
  if (u >= 1) return to;
  if (kind === "bool") return from;
  if (kind === "text") return u <= 0 ? from : ({ from: String(from), to: String(to), progress: u } satisfies Crossfade);
  if (kind === "color") return u <= 0 ? from : mixCss(from, to, Math.min(u, 1));
  if (kind === "point") return (from as number[]).map((x, i) => x + (((to as number[])[i] ?? x) - x) * u);
  return (from as number) + ((to as number) - (from as number)) * u;
}
