// Clicks (docs/reference.md, "Controls"): a click on a shape plays the animation of the nearest
// on-click up the scene tree whose when holds, as a button does.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

export class Clicks {
  private byShape = new Map<number, Obj[]>();

  constructor(private rt: Runtime) {
    for (const o of rt.objects) {
      if (o.kind === "on-click") this.byShape.set(o.shape!, [...(this.byShape.get(o.shape!) ?? []), o]);
    }
  }

  /** The on-click a click on shape hit sets off, if any. */
  find(hit: number): Obj | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byShape.get(i) ?? []).find(
        (l) => !l.when || Boolean(this.rt.evaluate(l.when as never)),
      );
      if (listener) return listener;
    }
    return null;
  }
}
