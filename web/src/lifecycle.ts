// The lifecycle of each canvas, copy by copy (docs/canvas-lifecycle.md; the author, 2026-11-13).
// State -1 is the values at page load. A copy's on-view plays when the copy first comes into
// view, if the scene still has the values at page load. A copy is ready at the moment nothing
// stands between it and the reader's input: when its on-view ends, or at page load if it has
// none. It stays ready from then on, and its on-ready plays then, unless it already runs from
// another copy of the canvas.
import type { Scheduler } from "./animate.ts";
import type { Obj } from "./doc.ts";
import type { Player } from "./player.ts";
import type { Runtime } from "./runtime.ts";
import { same } from "./same.ts";

interface Canvas {
  views: number[];
  readies: number[];
  // The values its on-views move, as they were at page load.
  atLoad: Map<string, unknown>;
}

export class Lifecycle {
  private canvases = new Map<number, Canvas>();
  // The writer of each on-view and on-ready in each copy, by listener.
  private writers = new Map<number, Map<Element, object>>();

  constructor(
    private rt: Runtime,
    private scheduler: Scheduler,
    private player: (o: Obj) => Player | null,
    private active: (i: number) => boolean,
  ) {
    const keys = (i: number) =>
      (player(rt.objects[i]!)?.targets ?? []).flatMap((t) => {
        const at = t.indexOf(":");
        return rt.slotsOf(Number(t.slice(0, at)), t.slice(at + 1) || null);
      });
    rt.objects.forEach((o, c) => {
      if (o.kind !== "canvas") return;
      const views = listeners(rt, "on-view", c);
      const atLoad = new Map(views.flatMap(keys).map((k) => [k, rt.freeValue(k)]));
      this.canvases.set(c, { views, readies: listeners(rt, "on-ready", c), atLoad });
    });
  }

  /**
   * Whether a copy of the view may be ready now: a canvas with no on-view always may; one with an
   * on-view once the copy has come into view and no on-view of the canvas runs from any copy, so
   * its own on-view has ended, by its end or by being cancelled, or was not triggered.
   */
  free(view: number, seen: boolean): boolean {
    const c = this.canvases.get(view);
    if (!c || c.views.length === 0) return true;
    return seen && !c.views.some((i) => [...(this.writers.get(i)?.values() ?? [])].some((w) => this.scheduler.runs(w)));
  }

  /** A copy of the view came into view for the first time: its on-views play, if the values they
   * move still have their values at page load. */
  seen(copy: Element, view: number): void {
    const c = this.canvases.get(view);
    if (!c) return;
    for (const [k, v] of c.atLoad) if (!same(this.rt.freeValue(k), v)) return;
    for (const i of c.views) this.play(i, copy);
  }

  /** A copy of the view became ready: its on-readies play, each unless it already runs from
   * another copy of the view. */
  ready(copy: Element, view: number): void {
    const c = this.canvases.get(view);
    if (!c) return;
    for (const i of c.readies) {
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
