// Plays an animation: its steps laid out in time (in-order one after another, at-once together,
// each as long as its longest part), and each move written to its variable or attribute as time passes or as a
// slider scrubs through it (docs/reference.md, "Transitions and animations" and "Controls").
import type { Clamp, Step } from "./doc.ts";
import { equal } from "./builtins.ts";
import type { Runtime } from "./runtime.ts";
import { type Ease, type Moves, along, applyEase, noneEnds } from "./transitions.ts";

interface Move {
  id: number;
  attr: string | null;
  transition: number;
  start: number;
  // Its place among the steps of an in-order that start at the same instant, as moves that take
  // no time do: a later one reads what the earlier ones wrote.
  stage: number;
  duration: number;
  ease: Ease;
  // Read once, when the move starts (docs/mtpc.md, "Transitions").
  from?: unknown;
  to?: unknown;
  // The loops around it, outermost first, and the rounds it was last written in.
  loops: Loop[];
  // The top-level step it is in.
  top: number;
  rounds?: string;
}

interface Loop {
  start: number;
  round: number;
  times: number;
}

/** A top-level step's span in time, for a play's bars. */
export interface Span {
  start: number;
  end: number;
}

export class Player {
  readonly duration: number;
  readonly spans: Span[];
  private moves: Move[] = [];
  private stage = 0;
  private at = 0;
  // A loop around the whole body: the step buttons are its body's items.
  private outer: Loop | null = null;
  // The values at a slider's stops, and the values they were worked out from.
  private table: { inputs: unknown[]; max: number; values: unknown[] } | null = null;
  private keeps: boolean | null = null;
  // The in-order whose items are the top-level steps, if there is one; whether a rest has put a
  // wait between each pair of them; and the step being laid out.
  private body: Step | null = null;
  private rested = false;
  private topNow = 0;
  // Moves of this top-level step and later ones are held from starting: a stepper stopped at the
  // end of a step leaves the next one's moves undone, even those that start at that instant.
  private upTo = Number.POSITIVE_INFINITY;
  /** Whether what it writes is part of the rest state, as an on-view's writes are (mtp-wjtd). */
  rest = false;

  constructor(
    private rt: Runtime,
    animation: number,
    private clamps: Clamp[] = [],
    rest = 0,
  ) {
    let root = rt.objects[animation]!.steps!;
    let body = root[0] === "loop" ? root[2] : root;
    const top = body[0] === "in-order" ? (body.slice(1) as Step[]) : [body];
    // A play's (rest t) is a wait between each pair of steps, in every round of a loop.
    if (rest > 0 && top.length > 1) {
      body = ["in-order", ...top.flatMap((s, k): Step[] => (k ? [["wait", rest], s] : [s]))];
      root = root[0] === "loop" ? ["loop", root[1], body] : body;
    }
    if (body[0] === "in-order") this.body = body;
    this.rested = rest > 0 && top.length > 1;
    this.duration = this.layout(root, 0, []);
    if (root[0] === "loop") this.outer = { start: 0, round: length(body), times: root[1] ?? Number.POSITIVE_INFINITY };
    let t = 0;
    this.spans = top.map((s) => {
      const d = length(s);
      const span = { start: t, end: t + d };
      t += d + rest;
      return span;
    });
  }

  // A loop's body is laid out once; seek maps the time into the round it falls in.
  private layout(step: Step, start: number, loops: Loop[]): number {
    if (step[0] === "move") {
      const [, [id, attr], transition, duration, ease] = step;
      this.moves.push({ id, attr, transition, start, stage: this.stage, duration, ease: ease as Ease, loops, top: this.topNow });
      return duration;
    }
    if (step[0] === "wait") return step[1];
    if (step[0] === "loop") {
      const loop = { start, round: length(step[2]), times: step[1] ?? Number.POSITIVE_INFINITY };
      this.layout(step[2], start, [...loops, loop]);
      return loop.round * loop.times;
    }
    let longest = 0;
    let t = start;
    const first = this.stage;
    let last = first;
    (step.slice(1) as Step[]).forEach((s, k) => {
      if (step === this.body) this.topNow = this.rested ? Math.ceil(k / 2) : k;
      if (step[0] === "at-once") this.stage = first;
      const d = this.layout(s, step[0] === "in-order" ? t : start, loops);
      if (step[0] === "in-order") {
        t += d;
        this.stage++;
      }
      last = Math.max(last, this.stage);
      longest = Math.max(longest, d);
    });
    this.stage = last;
    return step[0] === "in-order" ? t - start : longest;
  }

  /** How far in it stands, in seconds. */
  get time(): number {
    return this.at;
  }

  get done(): boolean {
    return this.at >= this.duration;
  }

  /** Where it stands in its round: the time, for an animation that does not loop as a whole. */
  get position(): number {
    return inRound(this.outer ? [this.outer] : [], this.at)[0];
  }

  /** The variables and attributes it writes, as "id:attr". */
  get targets(): string[] {
    return [...new Set(this.moves.map((m) => `${m.id}:${m.attr ?? ""}`))];
  }

  /** Holds the moves of the top-level steps from the kth on from starting, from the next seek. */
  holdFrom(k: number): void {
    this.upTo = k;
  }

  /** Writes every move as it stands t seconds in. */
  seek(time: number): void {
    // The page hears of a frame's writes once, at its end: a round may write many times.
    this.rt.together(() => (this.rest ? this.rt.asRest(() => this.seekNow(time)) : this.seekNow(time)));
  }

  private seekNow(time: number): void {
    const back = time < this.at;
    this.at = time;
    const shown = this.moves;
    const held = (m: Move) => m.top >= this.upTo;
    if (back || shown.some((m) => held(m) && m.from !== undefined)) {
      // A move that has not started by then puts back the value it started from, the latest
      // first, so each thing moved ends at how it stood before the first of them; it reads its
      // ends again when it starts.
      const later = shown.filter((m) => m.from !== undefined && (held(m) || inRound(m.loops, time)[0] < m.start));
      for (const m of later.sort((a, b) => b.start - a.start || b.stage - a.stage)) {
        this.write(m, 0);
        forgetEnds(m);
      }
    }
    // A new round: the last one ends first, every move in the order it ends, so a later move's
    // end is not undone by an earlier one's; then each reads its ends again.
    const ending = shown.filter((m) => m.rounds !== undefined && m.from !== undefined && inRound(m.loops, time)[1] !== m.rounds);
    for (const m of ending.sort((a, b) => a.start + a.duration - (b.start + b.duration))) this.write(m, 1);
    for (const m of ending) forgetEnds(m);
    const now = shown.map((m) => {
      const [t, rounds] = inRound(m.loops, time);
      m.rounds = rounds;
      return { m, t, at: time - (t - m.start) };
    });
    // Each move reads its ends at the instant it starts (mtp-lm24), however late the frame comes:
    // the moves under way are first brought to that instant, so a move sees what the moves that
    // ended before it left, and then every move starting then reads, before any of them writes.
    const eps = (x: number) => 1e-9 * Math.max(1, Math.abs(x));
    const starting = now
      .filter(({ m, t }) => m.from === undefined && t >= m.start && !held(m))
      .sort((a, b) => (Math.abs(a.at - b.at) <= eps(a.at) ? a.m.stage - b.m.stage : a.at - b.at));
    for (let i = 0; i < starting.length; ) {
      const { at, m: lead } = starting[i]!;
      for (const { m } of now) {
        if (m.from === undefined) continue;
        const [t, rounds] = inRound(m.loops, at);
        if (rounds === m.rounds) this.write(m, progress(m, t));
      }
      const together = (x: (typeof starting)[number]) => x.at - at <= eps(at) && x.m.stage === lead.stage;
      for (; i < starting.length && together(starting[i]!); i++) this.read(starting[i]!.m);
    }
    for (const { m, t } of now) if (m.from !== undefined) this.write(m, progress(m, t));
  }

  /** A slider's knob at u in [0, 1]: each part takes a share of the track equal to its duration. */
  scrub(u: number): void {
    this.seek(Math.min(Math.max(u, 0), 1) * this.duration);
  }

  /** Forgets where each move started, so the next run starts from their values then. */
  release(): void {
    for (const m of this.moves) forgetEnds(m);
  }

  /**
   * The value its one target has with a slider's knob at u, worked out without writing, for a
   * slider following its target.
   */
  valueAt(u: number): unknown {
    const t = Math.min(Math.max(u, 0), 1) * this.duration;
    const rt = this.rt;
    const first = this.moves[0]!;
    let cur = rt.value(this.holder(first), first.attr);
    for (const m of this.moves) {
      if (t < m.start) break;
      const tr = rt.objects[m.transition]!;
      const from = tr.from ? rt.evaluate(tr.from) : (m.from ?? cur);
      const to = tr.to ? rt.evaluate(tr.to) : (m.to ?? cur);
      const p = m.duration > 0 ? Math.min((t - m.start) / m.duration, 1) : 1;
      const [kind, u] = noneEnds(from, to, m.ease, applyEase(m.ease, p, (id) => rt.fn(id)), this.movesAs(m));
      cur = along(from, to, u, kind);
    }
    return cur;
  }

  /**
   * valueAt at each of a slider's max + 1 stops. A slider follows its target after every change,
   * so the stops are kept while what they are worked out from stays the same: the target's
   * value and each move's ends.
   */
  valuesAt(max: number): unknown[] {
    // An ease that is a function of the file may read the model, so is not trusted to stay.
    this.keeps ??= this.moves.every((m) => typeof m.ease !== "object" || Array.isArray(m.ease));
    const inputs = this.keeps ? this.inputs() : null;
    const t = this.table;
    if (inputs && t && t.max === max && equal(t.inputs, inputs)) return t.values;
    const values = Array.from({ length: max + 1 }, (_, n) => this.valueAt(n / max));
    this.table = inputs ? { inputs, max, values } : null;
    return values;
  }

  // What valueAt reads besides the time: the target's value and each move's ends.
  private inputs(): unknown[] {
    const rt = this.rt;
    const first = this.moves[0]!;
    const out: unknown[] = [rt.value(this.holder(first), first.attr)];
    for (const m of this.moves) {
      const tr = rt.objects[m.transition]!;
      out.push(tr.from ? rt.evaluate(tr.from) : m.from, tr.to ? rt.evaluate(tr.to) : m.to);
    }
    return out;
  }

  /** The top-level step running at the current time, or null when none is. */
  stepNow(): number | null {
    const t = this.position;
    const k = this.spans.findIndex((s) => t >= s.start && t < s.end);
    return k < 0 ? null : k;
  }

  private read(m: Move): void {
    const rt = this.rt;
    const tr = rt.objects[m.transition]!;
    const here = rt.value(this.holder(m), m.attr);
    m.from = tr.from ? rt.evaluate(tr.from) : here;
    m.to = tr.to ? rt.evaluate(tr.to) : here;
  }

  private write(m: Move, p: number): void {
    const rt = this.rt;
    if (m.from === undefined) this.read(m);
    const [kind, e] = noneEnds(m.from, m.to, m.ease, applyEase(m.ease, p, (id) => rt.fn(id)), this.movesAs(m));
    const tr = rt.objects[m.transition]!;
    // A path runs between two values, so a move to or from none jumps instead.
    const path = tr.path && typeof tr.path === "object" && m.from !== null && m.to !== null ? (tr.path as { func: number }).func : null;
    let v = path === null ? along(m.from, m.to, e, kind) : rt.fn(path)([m.from, m.to, e], null);
    for (const c of this.clamps) {
      if (c.target[0] === m.id && c.target[1] === m.attr && typeof v === "number") v = rt.clamp(c, v);
    }
    rt.write(m.id, m.attr, v);
  }

  private movesAs(m: Move): Moves {
    // pos is not kept apart from x and y: it is the two of them, a point.
    if (m.attr === "pos") return "point";
    const t = this.rt.typeOf(m.id, m.attr) ?? this.memberType(m);
    const core = t === undefined ? "real" : this.rt.core(t);
    if (core === "real" || core === "int" || core === "ratio") return "number";
    if (core === "point" || core === "transform") return "point";
    if (core === "color") return "color";
    return "jump";
  }

  // A group's or an instance's attribute is each member's, so a move starts from, and has the
  // type of, the first member that holds it, looking into a container inside it when the first
  // member is one.
  private holder(m: Move): number {
    let id: number | undefined = m.id;
    while (id !== undefined && m.attr !== null && m.attr !== "pos" && this.rt.typeOf(id, m.attr) === undefined) {
      id = this.rt.objects[id]!.members?.[0];
    }
    return id ?? m.id;
  }

  private memberType(m: Move) {
    return this.rt.typeOf(this.holder(m), m.attr);
  }
}

// A time inside the loops given, as a time in their first round, and which round of each it is
// in; past a loop's last round it stays at the end of that round.
function inRound(loops: Loop[], t: number): [number, string] {
  let rounds = "";
  for (const l of loops) {
    if (t < l.start) break;
    const k = Math.min(Math.floor((t - l.start) / l.round), l.times - 1);
    t -= k * l.round;
    rounds += `${k},`;
  }
  return [t, rounds];
}

function forgetEnds(m: Move): void {
  delete m.from;
  delete m.to;
}

// How far along a move is at time t of its round.
function progress(m: Move, t: number): number {
  // A stop at a step's end is a sum of durations, so (end - start) / duration may fall a hair
  // short of 1, as (1.4 - 0.4) / 1 does.
  if (m.duration > 0) {
    const u = (t - m.start) / m.duration;
    return u >= 1 - 1e-9 ? 1 : Math.max(u, 0);
  }
  return t >= m.start ? 1 : 0;
}

function length(step: Step): number {
  if (step[0] === "move") return step[3];
  if (step[0] === "wait") return step[1];
  if (step[0] === "loop") return length(step[2]) * (step[1] ?? Number.POSITIVE_INFINITY);
  const parts = (step.slice(1) as Step[]).map(length);
  return step[0] === "in-order" ? parts.reduce((a, b) => a + b, 0) : Math.max(0, ...parts);
}
