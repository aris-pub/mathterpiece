// The lifecycle of each canvas, copy by copy (docs/canvas-lifecycle.md; the author, 2026-11-13).
// State -1 is the values at page load. A copy's on-view plays when the copy first comes into
// view, if the scene still has the values at page load. State 0 is the values once the on-view
// has played from the values at page load, worked out here when the model loads. A copy is at
// rest while the scene is in state 0, an on-rest loop's values left out, and its on-rest plays
// when it first is, unless it already runs from another copy of the canvas.
//
// Which values are compared is not decided yet: here, for each canvas, the values its own
// on-views and on-rests move, so a canvas with neither is always at rest.
import type { Scheduler } from "./animate.ts";
import type { Obj } from "./doc.ts";
import type { Player } from "./player.ts";
import type { Runtime } from "./runtime.ts";
import { same } from "./same.ts";

interface Canvas {
  views: number[];
  rests: number[];
  // The values its on-views move, and the values compared for its rest with their state 0.
  viewKeys: string[];
  zero: Map<string, unknown>;
}

export class Lifecycle {
  private atLoad: Map<string, unknown>;
  private canvases = new Map<number, Canvas>();
  // The writer of each on-view and on-rest in each copy, by listener.
  private writers = new Map<number, Map<Element, object>>();

  constructor(
    private rt: Runtime,
    private scheduler: Scheduler,
    private player: (o: Obj) => Player | null,
    private active: (i: number) => boolean,
  ) {
    this.atLoad = rt.freeValues();
    const keys = (i: number) =>
      (player(rt.objects[i]!)?.targets ?? []).flatMap((t) => {
        const at = t.indexOf(":");
        return rt.slotsOf(Number(t.slice(0, at)), t.slice(at + 1) || null);
      });
    const forever = (i: number) => !Number.isFinite(player(rt.objects[i]!)?.duration ?? 0);
    const loops = new Set<string>();
    rt.objects.forEach((o, i) => {
      if (o.kind === "on-rest" && forever(i)) for (const k of keys(i)) loops.add(k);
    });
    rt.objects.forEach((o, c) => {
      if (o.kind !== "canvas") return;
      const views = listeners(rt, "on-view", c);
      const rests = listeners(rt, "on-rest", c);
      const viewKeys = [...new Set(views.flatMap(keys))];
      const compared = [...new Set([...viewKeys, ...rests.filter((i) => !forever(i)).flatMap(keys)])].filter((k) => !loops.has(k));
      this.canvases.set(c, { views, rests, viewKeys, zero: this.stateZero(views, compared) });
    });
  }

  // The values once the on-views have played to their ends from the values at page load: each
  // is played at once, here, and the values at page load are put back.
  private stateZero(views: number[], compared: string[]): Map<string, unknown> {
    const rt = this.rt;
    const players = views
      .filter((i) => this.active(i))
      .map((i) => this.player(rt.objects[i]!))
      .filter((p): p is Player => p !== null && Number.isFinite(p.duration));
    rt.together(() => {
      for (const p of players) p.seek(p.duration);
    });
    const zero = new Map(compared.map((k) => [k, rt.freeValue(k)]));
    rt.putFree(this.atLoad);
    return zero;
  }

  /** Whether a copy of the view is at rest: the scene is in its state 0. */
  rest(view: number): boolean {
    const c = this.canvases.get(view);
    if (!c) return true;
    for (const [k, v] of c.zero) if (!same(this.rt.freeValue(k), v)) return false;
    return true;
  }

  /** A copy of the view came into view for the first time: its on-views play, if the scene still
   * has the values at page load. */
  seen(copy: Element, view: number): void {
    const c = this.canvases.get(view);
    if (!c || !c.viewKeys.every((k) => same(this.rt.freeValue(k), this.atLoad.get(k)))) return;
    for (const i of c.views) this.play(i, copy);
  }

  /** A copy of the view is at rest for the first time: its on-rests play, each unless it already
   * runs from another copy of the view. */
  rested(copy: Element, view: number): void {
    const c = this.canvases.get(view);
    if (!c) return;
    for (const i of c.rests) {
      const others = [...(this.writers.get(i) ?? new Map<Element, object>()).entries()].filter(([el]) => el !== copy);
      if (others.some(([, w]) => this.scheduler.runs(w))) continue;
      this.play(i, copy);
    }
  }

  private play(i: number, copy: Element): void {
    if (!this.active(i)) return;
    const o = this.rt.objects[i]!;
    const player = this.player(o);
    if (!player) return;
    let byCopy = this.writers.get(i);
    if (!byCopy) this.writers.set(i, (byCopy = new Map()));
    let writer = byCopy.get(copy);
    if (!writer) byCopy.set(copy, (writer = {}));
    this.scheduler.start(player, writer, { reader: false, priority: o.priority });
  }
}

function listeners(rt: Runtime, kind: string, view: number): number[] {
  const out: number[] = [];
  rt.objects.forEach((o, i) => {
    if (o.kind === kind && o.view === view) out.push(i);
  });
  return out;
}
