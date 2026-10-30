// Clicking: as on the web, a click is a press and a release on the same shape. It goes up the
// tree from that shape to the nearest node with an attached on-click listener, whose animation
// then runs.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

export class Clicks {
  private byNode = new Map<number, Obj[]>();

  constructor(private rt: Runtime) {
    for (const o of rt.objects) {
      if (o.kind !== "on-click" || o.node === undefined) continue;
      this.byNode.set(o.node, [...(this.byNode.get(o.node) ?? []), o]);
    }
  }

  /** The listener a click on object i reaches, if any. */
  find(hit: number): Obj | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byNode.get(i) ?? []).find((l) => this.attached(l));
      if (listener) return listener;
    }
    return null;
  }

  private attached(listener: Obj): boolean {
    const when = listener.when;
    return when === null || when === undefined || Boolean(this.rt.eval(when, null, {}));
  }
}
