// Listeners on a shape that play an animation (docs/reference.md, "Controls"): on-click,
// on-release, on-dragstart and on-dragend. As in the DOM, an event on a shape goes up the scene tree and plays
// every listener of its kind whose (active bool) holds, on the shape and on each container,
// until a listener with (stop-propagation true) stops it at its shape.
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

  /** The listeners an event on shape hit sets off, from the shape up. */
  find(hit: number): Obj[] {
    return bubble(this.rt, hit, (i) => this.byShape.get(i) ?? []);
  }
}

/** The listeners of an event on hit, up the scene tree from it, each shape's own given by
 * on: the active ones, stopping after a shape where one of them stops the event. */
export function bubble(rt: Runtime, hit: number | null, on: (shape: number) => Obj[]): Obj[] {
  const found: Obj[] = [];
  for (let i = hit; i !== null; i = rt.parent(i)) {
    const here = on(i).filter((l) => holds(rt, l.active));
    found.push(...here);
    if (here.some((l) => holds(rt, l["stop-propagation"], false))) break;
  }
  return found;
}

/** Whether an optional bool attribute holds, absent giving otherwise. */
export function holds(rt: Runtime, attribute: unknown, otherwise = true): boolean {
  return attribute === null || attribute === undefined ? otherwise : Boolean(rt.evaluate(attribute as never));
}
