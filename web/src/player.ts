// Plays one animation from the JSON. Its pairs are laid out on a timeline: in-order puts them one
// after another, at-once side by side. A pair starts from wherever its targets are when its moment
// comes, and its ends that read the scene are read then too. The same timeline can be run by a
// clock (seek) or scrubbed by a slider (scrub), where durations only share out the track.
import type { Expr } from "./doc.ts";
import type { Runtime } from "./runtime.ts";
import {
  type Call,
  type Crossfade,
  type Ease,
  type Spec,
  type ValueKind,
  applyEase,
  endOf,
  totalDuration,
  trackWeight,
  valueAt,
  valueAtProgress,
} from "./transitions.ts";

type Target = [number, string];

// A composite's own ease, which warps time across everything inside it.
interface Warp {
  start: number;
  length: number;
  ease: Ease;
}

interface Segment {
  targets: Target[];
  kind: ValueKind;
  json: unknown;
  defaults: { duration?: number; ease?: Ease };
  // Where it sits by the clock (seconds) and on a slider's track (shares).
  start: number;
  length: number;
  trackStart: number;
  trackLength: number;
  warps: Warp[];
  trackWarps: Warp[];
  step: number;
  // While running by the clock: whether it has started, its start values and its ends, and
  // whether it is finished (or skipped by a jump).
  started: boolean;
  finished: boolean;
  starts: unknown[];
  spec: Spec | null;
}

export interface Step {
  start: number;
  segments: Segment[];
}

export class Player {
  readonly duration: number;
  readonly steps: Step[] = [];
  private segments: Segment[] = [];
  private trackTotal: number;
  private time = 0;
  // A slider's start values and ends, read when the reader takes hold of the knob.
  private scrubbing: { starts: Map<Segment, unknown[]>; specs: Map<Segment, Spec> } | null = null;

  constructor(
    private rt: Runtime,
    animation: number,
  ) {
    const body = rt.obj(animation).body;
    const top = Array.isArray(body) && body[0] === "in-order" ? (body.slice(2) as unknown[]) : [body];
    const settings = Array.isArray(body) && body[0] === "in-order" ? (body[1] as Settings) : {};
    // The steps of a play are the parts of its top-level in-order, without its waits.
    let clock = 0;
    let track = 0;
    const warps = settings.ease === undefined ? [] : [{ start: 0, length: 0, ease: settings.ease }];
    const trackWarps = settings.ease === undefined ? [] : [{ start: 0, length: 0, ease: settings.ease }];
    const defaults = defaultsOf(settings, {});
    for (const part of top) {
      const isWait = Array.isArray(part) && part[0] === "wait";
      const before = this.segments.length;
      const [length, weight] = this.layout(part, clock, track, defaults, warps, trackWarps, this.steps.length);
      if (!isWait) this.steps.push({ start: clock, segments: this.segments.slice(before) });
      clock += length;
      track += weight;
    }
    for (const w of warps) w.length = clock;
    for (const w of trackWarps) w.length = track;
    this.duration = clock;
    this.trackTotal = track;
  }

  /** Where running by the clock stops: the end, unless a single step was asked for. */
  stopAt = Number.POSITIVE_INFINITY;

  get done(): boolean {
    return this.time >= Math.min(this.duration, this.stopAt);
  }

  /** Runs only step k from now on: it starts from wherever things are and stops at its end. */
  only(k: number): void {
    const step = this.steps[k];
    if (!step) return;
    this.jump(k);
    for (const s of this.segments) if (s.step > k) s.finished = true;
    this.stopAt = Math.max(step.start, ...step.segments.map((s) => s.start + s.length));
  }

  /** Every target this animation writes, as "id.attr". */
  get targets(): string[] {
    const out: string[] = [];
    for (const s of this.segments) for (const [id, attr] of s.targets) if (!out.includes(`${id}.${attr}`)) out.push(`${id}.${attr}`);
    return out;
  }

  /** Runs by the clock to t seconds after the start. */
  seek(t: number): void {
    this.time = t;
    for (const s of this.segments) {
      if (s.finished) continue;
      const local = warped(t, s.warps, this.call) - s.start;
      if (local < 0) continue;
      if (!s.started) this.begin(s);
      const at = Math.min(local, s.length);
      s.targets.forEach(([id, attr], k) => this.write(id, attr, valueAt(s.spec as Spec, s.starts[k], at, s.kind, this.call)));
      if (local >= s.length) {
        s.finished = true;
        for (const [id] of s.targets) this.rt.morphs.delete(id);
      }
    }
  }

  /** Jumps to step k, which then starts from wherever things are; earlier steps are skipped. */
  jump(k: number): void {
    const step = this.steps[k];
    if (!step) return;
    for (const s of this.segments) {
      s.started = false;
      s.finished = s.step < k;
    }
    this.seek(step.start);
  }

  /** Whether every target of step k has the value the step would leave it at. */
  holds(k: number): boolean {
    const step = this.steps[k];
    if (!step) return false;
    return step.segments.every((s) => {
      const spec = this.specOf(s);
      return s.targets.every(([id, attr]) => {
        const now = this.rt.resolved(this.rt.value(id, attr));
        return same(now, this.rt.resolved(endOf(spec, now)));
      });
    });
  }

  /** Writes the values for a slider's knob at u in [0, 1]. */
  scrub(u: number): void {
    const values = this.valuesAt(u);
    for (const [key, value] of values) {
      const [id, attr] = key;
      this.write(id, attr, value);
    }
  }

  /** Lets the next scrub read start values and ends afresh, as when the knob is taken hold of. */
  release(): void {
    this.scrubbing = null;
  }

  /** Where the knob belongs for the current value of a one-target animation; null otherwise. */
  knob(): number | null {
    if (this.targets.length !== 1) return null;
    const [id, attr] = this.segments[0]?.targets[0] as Target;
    const now = this.rt.value(id, attr);
    const off = (u: number) => distance(this.valuesAt(u)[0]?.[1], now);
    const samples = 256;
    let best = 0;
    for (let k = 1; k <= samples; k++) if (off(k / samples) < off(best / samples)) best = k;
    // Narrow down between the neighbors of the best sample.
    let lo = Math.max(best - 1, 0) / samples;
    let hi = Math.min(best + 1, samples) / samples;
    for (let k = 0; k < 40; k++) {
      const a = lo + (hi - lo) / 3;
      const b = hi - (hi - lo) / 3;
      if (off(a) < off(b)) hi = b;
      else lo = a;
    }
    this.release();
    return (lo + hi) / 2;
  }

  private valuesAt(u: number): [Target, unknown][] {
    if (!this.scrubbing) this.prepareScrub();
    const scrub = this.scrubbing as NonNullable<Player["scrubbing"]>;
    const place = Math.min(Math.max(u, 0), 1) * this.trackTotal;
    const latest = new Map<string, [Segment, number]>();
    const first = new Map<string, [Segment, number]>();
    for (const s of this.segments) {
      const local = warped(place, s.trackWarps, this.call) - s.trackStart;
      s.targets.forEach(([id, attr], k) => {
        const key = `${id}.${attr}`;
        if (!first.has(key)) first.set(key, [s, k]);
        if (local >= 0) latest.set(key, [s, k]);
      });
    }
    const out: [Target, unknown][] = [];
    for (const [key, [s0, k0]] of first) {
      const [s, k] = latest.get(key) ?? [s0, k0];
      const local = warped(place, s.trackWarps, this.call) - s.trackStart;
      const p = s.trackLength > 0 ? Math.min(Math.max(local / s.trackLength, 0), 1) : 1;
      const spec = scrub.specs.get(s) as Spec;
      const start = (scrub.starts.get(s) as unknown[])[k];
      out.push([s.targets[k] as Target, valueAtProgress(spec, start, p, s.kind, this.call)]);
    }
    return out;
  }

  // Ends are read now; each target's later segments start where its earlier ones leave it.
  private prepareScrub(): void {
    const starts = new Map<Segment, unknown[]>();
    const specs = new Map<Segment, Spec>();
    const last = new Map<string, unknown>();
    for (const s of [...this.segments].sort((a, b) => a.trackStart - b.trackStart)) {
      const spec = this.specOf(s);
      specs.set(s, spec);
      const begins = s.targets.map(([id, attr]) => {
        const key = `${id}.${attr}`;
        return last.has(key) ? last.get(key) : this.rt.value(id, attr);
      });
      starts.set(s, begins);
      s.targets.forEach(([id, attr], k) => last.set(`${id}.${attr}`, endOf(spec, begins[k])));
    }
    this.scrubbing = { starts, specs };
  }

  private begin(s: Segment): void {
    s.started = true;
    s.starts = s.targets.map(([id, attr]) => this.rt.value(id, attr));
    s.spec = this.specOf(s);
  }

  // The segment's transition, with its ends read now and its composite's defaults around it.
  private specOf(s: Segment): Spec {
    const spec = toSpec(s.json, (e) => this.rt.eval(e, null, {}));
    if (s.defaults.duration === undefined && s.defaults.ease === undefined) return spec;
    return {
      kind: "in-order",
      parts: [spec],
      ...(s.defaults.duration === undefined ? {} : { defaultDuration: s.defaults.duration }),
      ...(s.defaults.ease === undefined ? {} : { defaultEase: s.defaults.ease }),
    };
  }

  private write(id: number, attr: string, value: unknown): void {
    if (isCrossfade(value)) {
      this.rt.write(id, attr, value.to);
      this.rt.morphs.set(id, [value.from, value.progress]);
      return;
    }
    if (typeof value === "string" && this.rt.kind(id) === "text") this.rt.morphs.delete(id);
    this.rt.write(id, attr, value);
  }

  private call: Call = (name, args) =>
    name in this.rt.doc.functions ? this.rt.callFunction(name, args, null) : this.rt.apply(name, args);

  // Lays out part, starting at clock and track, and returns how long it takes on each.
  private layout(
    part: unknown,
    clock: number,
    track: number,
    defaults: Segment["defaults"],
    warps: Warp[],
    trackWarps: Warp[],
    step: number,
  ): [number, number] {
    const [head, ...rest] = part as [string, ...unknown[]];
    if (head === "wait") return [rest[0] as number, rest[0] as number];
    if (head === "animation") {
      return this.layout(this.rt.obj(rest[0] as number).body, clock, track, defaults, warps, trackWarps, step);
    }
    if (head === "pair") {
      const [targets, kind, json] = rest as [Target[], ValueKind, unknown];
      const shape = withDefaults(toSpec(json, () => 0), defaults);
      const length = shape.kind === "single" && shape.duration === undefined ? 0 : safeDuration(shape);
      const weight = trackWeight(shape);
      this.segments.push({
        targets, kind, json, defaults, start: clock, length, trackStart: track, trackLength: weight,
        warps, trackWarps, step, started: false, finished: false, starts: [], spec: null,
      });
      return [length, weight];
    }
    const settings = rest[0] as Settings;
    const inner = defaultsOf(settings, defaults);
    const parts = rest.slice(1);
    const own = settings.ease === undefined ? null : { start: clock, length: 0, ease: settings.ease };
    const ownTrack = settings.ease === undefined ? null : { start: track, length: 0, ease: settings.ease };
    const innerWarps = own ? [...warps, own] : warps;
    const innerTrackWarps = ownTrack ? [...trackWarps, ownTrack] : trackWarps;
    let length = 0;
    let weight = 0;
    for (const p of parts) {
      const [l, w] =
        head === "in-order"
          ? this.layout(p, clock + length, track + weight, inner, innerWarps, innerTrackWarps, step)
          : this.layout(p, clock, track, inner, innerWarps, innerTrackWarps, step);
      length = head === "in-order" ? length + l : Math.max(length, l);
      weight = head === "in-order" ? weight + w : Math.max(weight, w);
    }
    if (own) own.length = length;
    if (ownTrack) ownTrack.length = weight;
    return [length, weight];
  }
}

type Settings = { ease?: Ease; "default-duration"?: number; "default-ease"?: Ease };

function defaultsOf(settings: Settings, outer: Segment["defaults"]): Segment["defaults"] {
  const out: Segment["defaults"] = { ...outer };
  if (settings["default-duration"] !== undefined) out.duration = settings["default-duration"];
  if (settings["default-ease"] !== undefined) out.ease = settings["default-ease"];
  return out;
}

function withDefaults(spec: Spec, defaults: Segment["defaults"]): Spec {
  if (defaults.duration === undefined && defaults.ease === undefined) return spec;
  return {
    kind: "in-order",
    parts: [spec],
    ...(defaults.duration === undefined ? {} : { defaultDuration: defaults.duration }),
    ...(defaults.ease === undefined ? {} : { defaultEase: defaults.ease }),
  };
}

// A slider's transitions may lack durations; by the clock they count as instant.
function safeDuration(spec: Spec): number {
  try {
    return totalDuration(spec);
  } catch {
    return 0;
  }
}

// Time t, as the composites around a segment warp it, outermost first.
function warped(t: number, warps: Warp[], call: Call): number {
  let out = t;
  for (const w of warps) {
    if (w.length <= 0) continue;
    const p = Math.min(Math.max((out - w.start) / w.length, 0), 1);
    out = w.start + applyEase(w.ease, p, call) * w.length;
  }
  return out;
}

/** A transition from the JSON, with its ends read by readEnd. */
export function toSpec(json: unknown, readEnd: (e: Expr) => unknown): Spec {
  const [head, ...rest] = json as [string, ...unknown[]];
  if (head === "wait") return { kind: "wait", duration: rest[0] as number };
  if (head === "in-order") {
    const settings = rest[0] as Settings;
    return {
      kind: "in-order",
      parts: rest.slice(1).map((p) => toSpec(p, readEnd)),
      ...(settings.ease === undefined ? {} : { ease: settings.ease }),
      ...(settings["default-duration"] === undefined ? {} : { defaultDuration: settings["default-duration"] }),
      ...(settings["default-ease"] === undefined ? {} : { defaultEase: settings["default-ease"] }),
    };
  }
  const parts = rest[0] as { from?: Expr; to?: Expr; duration?: number; ease?: Ease; path?: ["fn", string] };
  return {
    kind: "single",
    ...("from" in parts ? { from: readEnd(parts.from) } : {}),
    ...("to" in parts ? { to: readEnd(parts.to) } : {}),
    ...(parts.duration === undefined ? {} : { duration: parts.duration }),
    ...(parts.ease === undefined ? {} : { ease: parts.ease }),
    ...(parts.path === undefined ? {} : { path: parts.path }),
  };
}

function isCrossfade(value: unknown): value is Crossfade {
  return typeof value === "object" && value !== null && "progress" in value && "from" in value;
}

function same(a: unknown, b: unknown): boolean {
  return distance(a, b) <= 1e-9 * Math.max(1, magnitude(a));
}

function magnitude(a: unknown): number {
  if (typeof a === "number") return Math.abs(a);
  if (Array.isArray(a)) return Math.max(...a.map((x) => Math.abs(Number(x))), 0);
  return 0;
}

// How far apart two values are: for numbers and points, the usual distance; otherwise 0 or 1.
function distance(a: unknown, b: unknown): number {
  if (typeof a === "number" && typeof b === "number") return Math.abs(a - b);
  if (Array.isArray(a) && Array.isArray(b)) return Math.hypot(...a.map((x, i) => Number(x) - Number(b[i])));
  if (isCrossfade(a)) return distance(a.to, b);
  return a === b ? 0 : 1;
}
