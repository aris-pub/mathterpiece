// Listeners on a shape that play an animation (docs/reference.md, "Controls"): on-click,
// on-release, on-dragstart and on-dragend. As in the DOM, an event on a shape goes up the scene tree and plays
// every listener of its kind whose (active bool) holds, on the shape and on each container,
// until a listener with (stop-propagation true) stops it at its shape.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

export class Listeners {
  private byShape = new Map<number, Obj[]>();
  private tied = false;

  constructor(
    private rt: Runtime,
    kind: string,
  ) {
    for (const o of rt.objects) {
      if (o.kind !== kind) continue;
      this.byShape.set(o.shape!, [...(this.byShape.get(o.shape!) ?? []), o]);
      if (o.in) this.tied = true;
    }
  }

  /** The listeners an event on shape hit, in the view given, sets off, from the shape up. */
  find(hit: number, view?: number): Obj[] {
    // Drawing asks this of every shape, so a figure that ties no listener to a view filters none.
    const on = (i: number) => this.byShape.get(i) ?? [];
    return bubble(this.rt, hit, this.tied ? (i) => on(i).filter((l) => heardIn(l, view, this.rt)) : on);
  }
}

/** Whether a listener hears the pointer in a view: in every one, unless it names its own with
 * (in view…) (mtp-2juu.1), and then in those of them not quiet now (mtp-16z). No view given
 * means any. */
export function heardIn(listener: Obj, view?: number, rt?: Runtime): boolean {
  return view === undefined || !listener.in || (listener.in.includes(view) && !rt?.quiet.has(view) && !rt?.unready.has(view));
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
