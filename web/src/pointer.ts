// The pointer over a canvas (docs/reference.md, "Controls"). As JS's pointerenter and
// pointerleave, on-enter and on-leave play their animation when the pointer comes onto a shape or
// goes off it; as JS's pointermove, on-pointermove writes the pointer's position while it is over
// its shape or its canvas. As in JS, the pointer is over every shape up the scene tree from the
// one under it, so a group is entered from any of its members and left only when the pointer is
// off all of them.
import { apply, compose, invert } from "./builtins.ts";
import { bubble, heardIn, holds } from "./click.ts";
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

type Point = [number, number];

export class Pointer {
  private enters = new Map<number, Obj[]>();
  private leaves = new Map<number, Obj[]>();
  private moves: Obj[] = [];
  // The shapes the pointer is over, from the one under it up the scene tree.
  private over: number[] = [];

  constructor(
    private rt: Runtime,
    private canvas: number,
  ) {
    // Which views a listener is tied to never changes; whether they are quiet does, so that is
    // asked as the pointer moves.
    for (const o of rt.objects) {
      if (!heardIn(o, canvas)) continue;
      const into = o.kind === "on-enter" ? this.enters : o.kind === "on-leave" ? this.leaves : null;
      if (into) into.set(o.shape!, [...(into.get(o.shape!) ?? []), o]);
      if (o.kind === "on-pointermove" && (o.view === canvas || (o.shape ?? null) !== null)) this.moves.push(o);
    }
  }

  /** Whether an on-pointermove listens to the canvas itself. */
  get onCanvas(): boolean {
    return this.moves.some((l) => l.view === this.canvas);
  }

  /** Whether an active on-enter, on-leave or on-pointermove hears the pointer on the shape, its
   * own or a container's. */
  hears(shape: number): boolean {
    for (let i: number | null = shape; i !== null; i = this.rt.parent(i)) {
      if (this.active(this.enters, i).length || this.active(this.leaves, i).length) return true;
      if (this.moves.some((l) => l.shape === i && this.awake(l))) return true;
    }
    return false;
  }

  /** The pointer is now over the shape hit, or over no shape when hit is null: gives the on-leave
   * and on-enter listeners that sets off, in JS's order, leaves first, innermost first, then
   * enters, outermost first. */
  onto(hit: number | null): Obj[] {
    const now: number[] = [];
    for (let i = hit; i !== null; i = this.rt.parent(i)) now.push(i);
    const left = this.over.filter((i) => !now.includes(i));
    const entered = now.filter((i) => !this.over.includes(i)).reverse();
    this.over = now;
    return [...left.flatMap((i) => this.active(this.leaves, i)), ...entered.flatMap((i) => this.active(this.enters, i))];
  }

  /** Writes the pointer's position, a point in scene coordinates, for the on-pointermove
   * listeners the move reaches: as in the DOM, those up the scene tree from the shape under the
   * pointer and then the canvas's, until one stops it. Each first gives claim what it writes, as
   * "id:attr", and writes only when claim allows it (docs/reference.md, "Concurrency"). */
  move(scene: Point, claim: (targets: string[], listener: Obj) => boolean): void {
    const rt = this.rt;
    const onShapes = bubble(rt, this.over[0] ?? null, (i) => this.moves.filter((l) => l.shape === i && this.heard(l)));
    const stopped = onShapes.some((l) => holds(rt, l["stop-propagation"], false));
    const onCanvas = stopped ? [] : this.moves.filter((l) => l.view === this.canvas && holds(rt, l.active));
    rt.together(() => {
      for (const l of [...onShapes, ...onCanvas]) {
        if (claim([`${l.target![0]}:${l.target![1] ?? ""}`], l)) this.write(l, scene);
      }
    });
  }

  private active(listeners: Map<number, Obj[]>, shape: number): Obj[] {
    return (listeners.get(shape) ?? []).filter((l) => this.awake(l));
  }

  private heard(l: Obj): boolean {
    return heardIn(l, this.canvas, this.rt.quiet);
  }

  private awake(l: Obj): boolean {
    return this.heard(l) && holds(this.rt, l.active);
  }

  private write(l: Obj, scene: Point): boolean {
    const rt = this.rt;
    const [id, attr] = l.target!;
    if (rt.objects[id]!.kind === "variable") return rt.write(id, attr, scene);
    // A translate moves its shape within its container's frame.
    if (attr === "translate") return rt.write(id, attr, apply(invert(rt.toScene(rt.parent(id))), scene));
    if (attr !== "pos") return rt.write(id, attr, scene);
    // A shape's own position, in the frame its x and y live in, so the shape lands under the
    // pointer; each is limited by its own conditions.
    const m = compose(rt.local(id), rt.toScene(rt.parent(id)));
    const [x, y] = apply(invert(m), scene) as Point;
    const clamped = (a: string, v: number) => {
      for (const c of l.conditions ?? []) if (c.target[0] === id && c.target[1] === a) v = rt.clamp(c, v);
      return v;
    };
    const wx = rt.write(id, "x", clamped("x", x));
    return rt.write(id, "y", clamped("y", y)) || wx;
  }
}
