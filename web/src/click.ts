// Listeners on a shape that play an animation (docs/reference.md, "Controls"): on-click,
// on-release and on-dragend. An event on a shape plays the animation of the nearest listener of
// its kind up the scene tree whose when holds, as a button does.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

export class Listeners {
  private byShape = new Map<number, Obj[]>();

  constructor(
    private rt: Runtime,
    kind: string,
  ) {
    for (const o of rt.objects) {
      if (o.kind === kind) this.byShape.set(o.shape!, [...(this.byShape.get(o.shape!) ?? []), o]);
    }
  }

  /** The listener an event on shape hit sets off, if any. */
  find(hit: number): Obj | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byShape.get(i) ?? []).find(
        (l) => !l.active || Boolean(this.rt.evaluate(l.active as never)),
      );
      if (listener) return listener;
    }
    return null;
  }
}
