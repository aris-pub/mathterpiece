// Plays an animation: its steps laid out in time (in-order one after another, at-once together,
// each as long as its longest part), and each move written to its place as time passes or as a
// slider scrubs through it (docs/reference.md, "Transitions and animations" and "Controls").
import type { Clamp, Step } from "./doc.ts";
import type { Runtime } from "./runtime.ts";
import { type Ease, type Moves, along, applyEase } from "./transitions.ts";

interface Move {
  id: number;
  attr: string | null;
  transition: number;
  start: number;
  duration: number;
  ease: Ease;
  // Read once, when the move starts (docs/mtpc.md, "Transitions").
  from?: unknown;
  to?: unknown;
}

/** A top-level step's span in time, for play's step buttons. */
export interface Span {
  start: number;
  end: number;
}

export class Player {
  readonly duration: number;
  readonly spans: Span[];
  private moves: Move[] = [];
  private time = 0;

  constructor(
    private rt: Runtime,
    animation: number,
    private clamps: Clamp[] = [],
  ) {
    const root = rt.objects[animation]!.steps!;
    this.duration = this.layout(root, 0);
    const top = root[0] === "in-order" ? (root.slice(1) as Step[]) : [root];
    let t = 0;
    this.spans = top.map((s) => {
      const d = length(s);
      const span = { start: t, end: t + d };
      t += d;
      return span;
    });
  }

  private layout(step: Step, start: number): number {
    if (step[0] === "move") {
      const [, [id, attr], transition, duration, ease] = step;
      this.moves.push({ id, attr, transition, start, duration, ease: ease as Ease });
      return duration;
    }
    if (step[0] === "wait") return step[1];
    let longest = 0;
    let t = start;
    for (const s of step.slice(1) as Step[]) {
      const d = this.layout(s, step[0] === "in-order" ? t : start);
      if (step[0] === "in-order") t += d;
      longest = Math.max(longest, d);
    }
    return step[0] === "in-order" ? t - start : longest;
  }

  get done(): boolean {
    return this.time >= this.duration;
  }

  /** The places it writes, as "id:attr". */
  get targets(): string[] {
    return [...new Set(this.moves.map((m) => `${m.id}:${m.attr ?? ""}`))];
  }

  /** Writes every move as it stands t seconds in. */
  seek(t: number): void {
    this.time = t;
    for (const m of this.moves) {
      if (t < m.start && m.from === undefined) continue;
      const p = m.duration > 0 ? Math.min(Math.max((t - m.start) / m.duration, 0), 1) : t >= m.start ? 1 : 0;
      this.write(m, p);
    }
  }

  /** A slider's knob at u in [0, 1]: each part takes a share of the track equal to its duration. */
  scrub(u: number): void {
    this.seek(Math.min(Math.max(u, 0), 1) * this.duration);
  }

  /** Forgets where each move started, so the next run starts from where the places are then. */
  release(): void {
    for (const m of this.moves) {
      delete m.from;
      delete m.to;
    }
  }

  /** The top-level step running at the current time, or null when none is. */
  stepNow(): number | null {
    const k = this.spans.findIndex((s) => this.time >= s.start && this.time < s.end);
    return k < 0 ? null : k;
  }

  private write(m: Move, p: number): void {
    const rt = this.rt;
    if (m.from === undefined) {
      const tr = rt.objects[m.transition]!;
      const here = rt.value(m.id, m.attr);
      m.from = tr.from ? rt.placeValue(tr.from) : here;
      m.to = tr.to ? rt.placeValue(tr.to) : here;
    }
    const e = applyEase(m.ease, p, (id) => rt.fn(id));
    const tr = rt.objects[m.transition]!;
    const path = tr.path && typeof tr.path === "object" ? (tr.path as { func: number }).func : null;
    let v = path === null ? along(m.from, m.to, e, this.movesAs(m)) : rt.fn(path)([m.from, m.to, e], null);
    for (const c of this.clamps) {
      if (c.place[0] === m.id && c.place[1] === m.attr && typeof v === "number") v = rt.clamp(c, v);
    }
    rt.write(m.id, m.attr, v);
  }

  private movesAs(m: Move): Moves {
    const t = this.rt.typeOf(m.id, m.attr) ?? this.memberType(m);
    const core = t === undefined ? "real" : this.rt.core(t);
    if (core === "real" || core === "int" || core === "ratio") return "number";
    if (core === "point" || core === "transform") return "point";
    if (core === "color") return "color";
    if (m.attr === "pos") return "point";
    return "jump";
  }

  // A group's attribute is each member's, so its type is a member's.
  private memberType(m: Move) {
    const first = this.rt.objects[m.id]!.members?.[0];
    return first === undefined ? undefined : this.rt.typeOf(first, m.attr);
  }
}

function length(step: Step): number {
  if (step[0] === "move") return step[3];
  if (step[0] === "wait") return step[1];
  const parts = (step.slice(1) as Step[]).map(length);
  return step[0] === "in-order" ? parts.reduce((a, b) => a + b, 0) : Math.max(0, ...parts);
}
