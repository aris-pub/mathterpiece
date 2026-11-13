// The lifecycle of each canvas (docs/canvas-lifecycle.md; the author, 2026-11-13). State -1 is
// the values at page load. A copy's on-view plays, at priority 1000, when the copy first comes
// into view, if the values it moves still have their values at page load. A canvas is ready, in
// every copy at once, from the first moment the on-view of one of its copies has ended, or from
// page load when it has none, and stays ready. Its on-ready plays once, then. Until it is ready,
// the listeners inside it hear nothing and the controls that belong to it take no input.
import { VIEW, type Scheduler } from "./animate.ts";
import type { Obj } from "./doc.ts";
import type { Player } from "./player.ts";
import type { Runtime } from "./runtime.ts";
import { same } from "./same.ts";

interface Canvas {
  views: number[];
  readies: number[];
  // The values its on-views move, as they were at page load.
  atLoad: Map<string, unknown>;
  // Whether a copy of it has come into view, and whether its on-readies have been triggered.
  seen: boolean;
  readied: boolean;
}

export class Lifecycle {
  private canvases = new Map<number, Canvas>();
  // The writer of each on-view in each copy, by listener, and of each on-ready, one per canvas.
  private writers = new Map<number, Map<Element | null, object>>();

  constructor(
    private rt: Runtime,
    private scheduler: Scheduler,
    private player: (o: Obj) => Player | null,
    private active: (i: number) => boolean,
    // Called when a canvas becomes ready, so every element shows it.
    private changed: () => void,
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
      this.canvases.set(c, { views, readies: listeners(rt, "on-ready", c), atLoad, seen: false, readied: false });
      if (views.length > 0) rt.unready.add(c);
    });
  }

  /** Whether the view is ready. A display and a readout always are. */
  ready(view: number): boolean {
    return !this.rt.unready.has(view);
  }

  /** A copy of the view came into view for the first time: its on-views play, if the values they
   * move still have their values at page load. */
  seen(copy: Element, view: number): void {
    const c = this.canvases.get(view);
    if (!c) return;
    c.seen = true;
    let fresh = true;
    for (const [k, v] of c.atLoad) if (!same(this.rt.freeValue(k), v)) fresh = false;
    if (fresh && !this.ready(view)) for (const i of c.views) this.play(i, copy);
    this.check(view);
  }

  /**
   * Makes the view ready when it is time, and plays its on-readies the first time it is: a
   * canvas with an on-view once a copy has come into view and no on-view of it runs from any
   * copy. That is when the first on-view to end has ended, unless another copy's still runs; a
   * copy whose on-view was not triggered and none runs makes it ready at once, which the author
   * has not decided.
   */
  check(view: number): void {
    const c = this.canvases.get(view);
    if (!c) return;
    if (!this.ready(view)) {
      const running = c.views.some((i) => [...(this.writers.get(i)?.values() ?? [])].some((w) => this.scheduler.runs(w)));
      if (!c.seen || running) return;
      this.rt.unready.delete(view);
    }
    if (c.readied) return;
    c.readied = true;
    for (const i of c.readies) this.play(i, null);
    this.changed();
  }

  private play(i: number, copy: Element | null): void {
    if (!this.active(i)) return;
    const o = this.rt.objects[i]!;
    const player = this.player(o);
    if (!player) return;
    let byCopy = this.writers.get(i);
    if (!byCopy) this.writers.set(i, (byCopy = new Map()));
    let writer = byCopy.get(copy);
    if (!writer) byCopy.set(copy, (writer = {}));
    const priority = o.priority ?? (o.kind === "on-view" ? VIEW : undefined);
    this.scheduler.start(player, writer, { reader: false, priority });
  }
}

function listeners(rt: Runtime, kind: string, view: number): number[] {
  const out: number[] = [];
  rt.objects.forEach((o, i) => {
    if (o.kind === kind && o.view === view) out.push(i);
  });
  return out;
}
