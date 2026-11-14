// on-show and on-hide (docs/reference.md, "Showing and hiding"; mtp-7i3j). While one plays, its
// canvas draws a stand-in in place of the shape: a copy that canvas alone has, which no other
// view, writer or the scene sees, hears or reads. The animation moves the stand-in and never the
// scene. Each attribute of the stand-in follows the original's as the scene changes it: one that
// a move moves is the original's value plus an offset the move moves (for a color, a blend from
// the move's value to the original's), so the stand-in ends where the original is; drawn is
// moved as it is. When the animation ends, the canvas draws the original again (on-show) or
// stops drawing the shape (on-hide), and drops the stand-in.
import type { Obj } from "./doc.ts";
import type { Scheduler } from "./animate.ts";
import { Player, type Stage, type StageMove } from "./player.ts";
import { Runtime, percent } from "./runtime.ts";
import type { Showing } from "./svg.ts";
import { along } from "./transitions.ts";

// A shape is hidden (drawn 0 and opacity 0), shown as the scene gives it, or drawn by a stand-in
// while its on-show or on-hide plays.
type Phase = "shown" | "hidden" | "showing" | "hiding";

// The original's value as it is now, at an end of a blend.
const LIVE = Symbol("live");

// An attribute a stand-in has apart from the original's.
type Own =
  | { kind: "value"; value: unknown }
  | { kind: "offset"; by: number | number[] }
  | { kind: "blend"; from: unknown; to: unknown; along: number };

interface Snapshot {
  values: Map<string, unknown>;
  css: Map<string, string | null>;
}

interface StandIn {
  own: Map<string, Own>;
  // For each attribute a move of it has started on: the stand-in's value then, the original's,
  // and whether the stand-in followed the original then.
  starts: Map<string, { now: unknown; base: unknown; live: boolean }>;
  // A shape that has stopped existing is drawn as it last was: it and each container around it.
  frozen: Map<number, Snapshot> | null;
}

interface Play {
  show: boolean;
  player: Player | null;
  time: number;
  leaves: Set<number>;
}

interface State {
  phase: Phase;
  standIn: StandIn | null;
  play: Play | null;
}

const CONTAINERS = new Set(["scene", "group", "instance"]);
const CORNERS: Record<string, string[]> = { line: ["from", "to"], curve: ["from", "to"], triangle: ["a", "b", "c"] };
const LISTS: Record<string, string[]> = { polyline: ["points"], polygon: ["points"], curve: ["controls"] };
const fromPoints = (kind: string) => kind in CORNERS || kind in LISTS;

function plus(a: unknown, b: number | number[]): unknown {
  if (typeof a === "number" && typeof b === "number") return a + b;
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, k) => (x as number) + (b[k] ?? 0));
  return a;
}

function minus(a: unknown, b: unknown): number | number[] {
  if (typeof a === "number" && typeof b === "number") return a - b;
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, k) => (x as number) - ((b[k] as number) ?? 0));
  return 0;
}

/** The on-show and on-hide of one canvas, and the stand-ins it draws while they play. */
export class Showings implements Showing {
  /** What the canvas draws from: the scene, with each stand-in in place of its shape. */
  readonly rt: Runtime;
  private listeners = new Map<number, { show: Obj | null; hide: Obj | null }>();
  // Each shape with an on-show or on-hide, and every container around one.
  private holding = new Set<number>();
  private states = new Map<number, State>();
  private plays = new Set<Play>();
  // The last values of each shown shape that may stop existing, for its frozen stand-in.
  private last = new Map<number, Map<number, Snapshot>>();
  private frozen = new Map<number, Snapshot>();
  // Whether the canvas has drawn its shapes once: the first time, they are as the scene gives them.
  private started = false;
  private ticking = false;

  constructor(
    private scene: Runtime,
    private canvas: number,
    private scheduler: Scheduler,
    private redraw: () => void,
  ) {
    const own = new Map<number, { show?: Obj; hide?: Obj }>();
    for (const o of scene.objects) {
      if ((o.kind !== "on-show" && o.kind !== "on-hide") || !o.in?.includes(canvas)) continue;
      const e = own.get(o.shape!) ?? {};
      e[o.kind === "on-show" ? "show" : "hide"] = o;
      own.set(o.shape!, e);
    }
    if (own.size === 0) {
      this.rt = scene;
      return;
    }
    const clips = new Set(scene.objects.flatMap((o) => (o.clip === undefined ? [] : [o.clip])));
    scene.objects.forEach((o, i) => {
      if (CONTAINERS.has(o.kind) || !o.attrs || clips.has(i) || !("opacity" in o.attrs)) return;
      // The most specific wins: a shape's own listener, then its nearest container's.
      let show: Obj | null = null;
      let hide: Obj | null = null;
      for (let j: number | null = i; j !== null; j = scene.parent(j)) {
        const e = own.get(j);
        show ??= e?.show ?? null;
        hide ??= e?.hide ?? null;
      }
      if (!show && !hide) return;
      this.listeners.set(i, { show, hide });
      this.states.set(i, { phase: "hidden", standIn: null, play: null });
      for (let j: number | null = i; j !== null; j = scene.parent(j)) this.holding.add(j);
    });
    this.rt = this.overlay();
  }

  // The scene as the canvas draws it: what is read of a shape drawn by a stand-in is the
  // stand-in's, and a frozen one exists still, with its last values.
  private overlay(): Runtime {
    const scene = this.scene;
    const rt = Object.create(scene) as Runtime;
    rt.value = (id: number, attr: string | null = null) => {
      if (attr === null) return scene.value(id, attr);
      if (this.states.get(id)?.standIn) return this.standInValue(id, attr);
      return this.original(id, attr);
    };
    rt.exists = (id: number) => scene.exists(id) || this.frozenAt(id) !== null;
    rt.css = (id: number, attr: string | null) => {
      if (attr === null) return scene.css(id, attr);
      if (this.states.get(id)?.standIn) return this.standInCss(id, attr);
      return this.originalCss(id, attr);
    };
    // A shape's frame read through the stand-ins only where one is in it: a row's places worked
    // out from a stand-in must not be kept for the scene.
    rt.local = (id: number, members = false, pixel = 0) => {
      const own = this.states.get(id)?.standIn?.own;
      if (this.frozenAt(id) || own?.has("translate") || own?.has("transform")) {
        return Runtime.prototype.local.call(rt, id, members, pixel);
      }
      return scene.local(id, members, pixel);
    };
    return rt;
  }

  /** Whether the canvas has any on-show or on-hide. */
  get any(): boolean {
    return this.listeners.size > 0;
  }

  around(id: number): boolean {
    return this.holding.has(id);
  }

  governs(id: number): boolean {
    return this.listeners.has(id);
  }

  hidden(id: number): boolean {
    return this.states.get(id)?.phase === "hidden";
  }

  standIn(id: number): boolean {
    return Boolean(this.states.get(id)?.standIn);
  }

  /** Whether an item's shape holds a stand-in still hiding, so the canvas keeps drawing it. */
  holds(id: number): boolean {
    for (const [leaf, s] of this.states) {
      if (s.phase !== "hiding") continue;
      for (let j: number | null = leaf; j !== null; j = this.scene.parent(j)) if (j === id) return true;
    }
    return false;
  }

  /** A shape's attribute as the canvas draws it, or null while the canvas does not draw it. */
  drawnAs(id: number, attr: string): unknown {
    if (this.hidden(id)) return null;
    return this.rt.value(id, attr);
  }

  /**
   * Starts an on-show for each shape the canvas starts showing, and an on-hide for each it stops
   * showing, given the shapes its items give now. A shape with no on-show is shown at once, and
   * one with no on-hide hidden at once, as before (mtp-7i3j). Until the canvas is ready, shapes
   * are shown and hidden at once: on-show and on-hide play only after state 0 (the author,
   * 2026-11-14). So are they when a play or a stepper sets a state, and while the reader drags a
   * play's bars.
   */
  follow(given: Set<number>): void {
    if (this.listeners.size === 0) return;
    const atOnce = !this.started || this.scene.unready.has(this.canvas) || this.scene.jumping;
    this.started = true;
    const starting = new Map<Obj, number[]>();
    const add = (l: Obj, leaf: number) => starting.set(l, [...(starting.get(l) ?? []), leaf]);
    for (const [leaf, l] of this.listeners) {
      const state = this.states.get(leaf)!;
      const exists = this.scene.exists(leaf);
      const drawn = state.phase === "shown" || state.phase === "showing";
      const wanted = exists && this.given(leaf, given);
      if (wanted && !drawn) {
        if (l.show && !atOnce) add(l.show, leaf);
        else this.settle(leaf, "shown");
      } else if (!wanted && drawn) {
        if (l.hide && !atOnce) add(l.hide, leaf);
        else this.settle(leaf, "hidden");
      }
    }
    for (const [listener, leaves] of starting) this.start(listener, leaves);
    for (const [leaf, l] of this.listeners) {
      const phase = this.states.get(leaf)!.phase;
      if (!l.hide || (phase !== "shown" && phase !== "showing") || !this.scene.mayVanish(leaf)) continue;
      if (this.scene.exists(leaf)) this.last.set(leaf, this.snapshot(leaf));
    }
  }

  private given(leaf: number, given: Set<number>): boolean {
    for (let j: number | null = leaf; j !== null; j = this.scene.parent(j)) if (given.has(j)) return true;
    return false;
  }

  private snapshot(leaf: number): Map<number, Snapshot> {
    const out = new Map<number, Snapshot>();
    for (let j: number | null = leaf; j !== null; j = this.scene.parent(j)) {
      const o = this.scene.objects[j]!;
      if (o.kind === "scene") break;
      const values = new Map<string, unknown>();
      const css = new Map<string, string | null>();
      for (const attr of Object.keys(o.attrs ?? {})) values.set(attr, this.scene.value(j, attr));
      for (const attr of ["fill", "stroke"]) if (values.has(attr)) css.set(attr, this.scene.css(j, attr));
      out.set(j, { values, css });
    }
    return out;
  }

  // A newcomer on a shape cancels what played on its stand-in before, and starts from the
  // stand-in as it is: half drawn, half faded (the author, 2026-11-11).
  private start(listener: Obj, leaves: number[]): void {
    const show = listener.kind === "on-show";
    const play: Play = { show, player: null, time: 0, leaves: new Set() };
    for (const leaf of leaves) {
      const state = this.states.get(leaf)!;
      this.leave(state, leaf);
      const exists = this.scene.exists(leaf);
      const frozen = exists ? null : (this.last.get(leaf) ?? state.standIn?.frozen ?? null);
      if (!exists && !frozen) {
        this.settle(leaf, "hidden");
        continue;
      }
      // Hidden is drawn 0 and opacity 0.
      const hidden = state.phase === "hidden";
      state.standIn ??= {
        own: new Map<string, Own>(
          hidden
            ? [
                ["drawn", { kind: "value", value: 0 }],
                ["opacity", { kind: "value", value: 0 }],
              ]
            : [],
        ),
        starts: new Map(),
        frozen: null,
      };
      state.standIn.starts.clear();
      state.standIn.frozen = frozen;
      state.phase = show ? "showing" : "hiding";
      state.play = play;
      play.leaves.add(leaf);
    }
    this.refreeze();
    if (play.leaves.size === 0) return;
    play.player = new Player(this.scene, listener.animation!, [], 0, this.stage(play));
    this.plays.add(play);
    play.player.seek(0);
    if (play.player.done) this.finish(play);
    else this.tick();
  }

  private leave(state: State, leaf: number): void {
    const play = state.play;
    state.play = null;
    if (!play) return;
    play.leaves.delete(leaf);
    if (play.leaves.size === 0) this.plays.delete(play);
  }

  private settle(leaf: number, phase: "shown" | "hidden"): void {
    const state = this.states.get(leaf)!;
    this.leave(state, leaf);
    state.phase = phase;
    const was = state.standIn?.frozen;
    state.standIn = null;
    if (was) this.refreeze();
  }

  private finish(play: Play): void {
    for (const leaf of [...play.leaves]) this.settle(leaf, play.show ? "shown" : "hidden");
    this.plays.delete(play);
  }

  private refreeze(): void {
    this.frozen.clear();
    for (const s of this.states.values()) for (const [id, snap] of s.standIn?.frozen ?? []) this.frozen.set(id, snap);
  }

  private frozenAt(id: number): Snapshot | null {
    if (this.frozen.size === 0 || this.scene.exists(id)) return null;
    return this.frozen.get(id) ?? null;
  }

  // On-show and on-hide write only stand-ins, so they meet no writer of the scene: the canvas
  // moves them with the clock itself.
  private tick(): void {
    if (this.ticking || this.plays.size === 0) return;
    this.ticking = true;
    this.scheduler.addTicker((seconds) => {
      for (const play of [...this.plays]) {
        play.time += seconds;
        play.player!.seek(play.time);
        if (play.player!.done) this.finish(play);
      }
      this.redraw();
      this.ticking = this.plays.size > 0;
      return this.ticking;
    });
  }

  // What a play's moves move: the stand-ins of its shapes. A move of a container's attribute
  // moves each of its shapes in the play, each from its own value.
  private stage(play: Play): Stage {
    const leavesOf = (id: number): number[] => {
      if (play.leaves.has(id)) return [id];
      return [...play.leaves].filter((leaf) => {
        for (let j: number | null = leaf; j !== null; j = this.scene.parent(j)) if (j === id) return true;
        return false;
      });
    };
    return {
      value: (id, attr) => {
        const [leaf] = leavesOf(id);
        return leaf === undefined ? this.scene.value(id, attr) : this.standInValue(leaf, attr!);
      },
      rest: (id, attr) => {
        const [leaf] = leavesOf(id);
        return leaf === undefined ? this.scene.value(id, attr) : this.original(leaf, attr!);
      },
      starts: (id, attr) => {
        for (const leaf of leavesOf(id)) {
          const s = this.states.get(leaf)!.standIn!;
          const live = attr === "pos" ? !s.own.has("x") && !s.own.has("y") && !s.own.has("pos") : !s.own.has(attr!);
          s.starts.set(attr!, { now: this.standInValue(leaf, attr!), base: this.original(leaf, attr!), live });
        }
      },
      write: (id, attr, value, move) => {
        for (const leaf of leavesOf(id)) this.put(leaf, id, attr!, value, move);
      },
    };
  }

  private put(leaf: number, id: number, attr: string, value: unknown, move: StageMove): void {
    const s = this.states.get(leaf)!.standIn!;
    const start = s.starts.get(attr);
    const from = move.fromGiven ? move.from : start?.now;
    const to = move.toGiven ? move.to : start?.base;
    const v = leaf === id ? value : along(from, to, move.along, move.moves);
    if (attr === "drawn" || move.moves === "jump") {
      s.own.set(attr, { kind: "value", value: v });
      return;
    }
    if (move.moves === "color") {
      const live = !move.fromGiven && start?.live;
      s.own.set(attr, { kind: "blend", from: live ? LIVE : from, to: move.toGiven ? to : LIVE, along: Math.min(Math.max(move.along, 0), 1) });
      return;
    }
    const base = start?.base ?? this.original(leaf, attr);
    const kind = this.scene.objects[leaf]!.kind;
    if (fromPoints(kind) && (attr === "pos" || attr === "x" || attr === "y")) {
      const was = s.own.get("pos");
      const by = was?.kind === "offset" ? (was.by as number[]) : [0, 0];
      const d = minus(v, base);
      const next = attr === "pos" ? (d as number[]) : attr === "x" ? [d as number, by[1]!] : [by[0]!, d as number];
      s.own.set("pos", { kind: "offset", by: next });
      return;
    }
    if (attr === "pos") {
      const d = minus(v, base) as number[];
      s.own.set("x", { kind: "offset", by: d[0]! });
      s.own.set("y", { kind: "offset", by: d[1]! });
      return;
    }
    s.own.set(attr, { kind: "offset", by: minus(v, base) });
  }

  // The original's value: the scene's, or its last one when it has stopped existing.
  private original(id: number, attr: string): unknown {
    const snap = this.frozenAt(id);
    if (!snap) return this.scene.value(id, attr);
    if (snap.values.has(attr)) return snap.values.get(attr);
    if (attr === "pos" && snap.values.has("x")) return [snap.values.get("x"), snap.values.get("y")];
    return null;
  }

  private originalCss(id: number, attr: string): string | null {
    const snap = this.frozenAt(id);
    return snap ? (snap.css.get(attr) ?? null) : this.scene.css(id, attr);
  }

  private standInValue(leaf: number, attr: string): unknown {
    const s = this.states.get(leaf)?.standIn;
    if (!s) return this.original(leaf, attr);
    // The reader acts on the shape, not on its stand-in.
    if (attr === "pointer-events") return false;
    const kind = this.scene.objects[leaf]!.kind;
    const moved = s.own.get("pos");
    if (fromPoints(kind) && moved?.kind === "offset") {
      const by = moved.by as number[];
      const here = this.original(leaf, attr);
      if (CORNERS[kind]?.includes(attr) || attr === "pos") return here === null ? null : plus(here, by);
      if (LISTS[kind]?.includes(attr)) return (here as number[][] | null)?.map((p) => plus(p, by)) ?? null;
      if (attr === "x" || attr === "y") return here === null ? null : (here as number) + by[attr === "x" ? 0 : 1]!;
    }
    if (attr === "pos" && !fromPoints(kind)) return [this.standInValue(leaf, "x"), this.standInValue(leaf, "y")];
    const own = s.own.get(attr);
    if (!own) return this.original(leaf, attr);
    if (own.kind === "value") return own.value;
    const here = this.original(leaf, attr);
    if (own.kind === "offset") return here === null ? null : this.scene.inRange(leaf, attr, plus(here, own.by));
    const end = (e: unknown) => (e === LIVE ? here : e);
    return along(end(own.from), end(own.to), own.along, "color");
  }

  private standInCss(leaf: number, attr: string): string | null {
    const own = this.states.get(leaf)?.standIn?.own.get(attr);
    if (!own || own.kind !== "blend") return own ? null : this.originalCss(leaf, attr);
    const live = this.originalCss(leaf, attr);
    if (live === null || (own.from !== LIVE && own.to !== LIVE)) return null;
    const css = (e: unknown) => (e === LIVE ? live : e === null ? "transparent" : String(e));
    if (own.along <= 0) return css(own.from);
    if (own.along >= 1) return css(own.to);
    return `color-mix(in srgb, ${css(own.from)} ${percent(1 - own.along)}, ${css(own.to)} ${percent(own.along)})`;
  }
}
