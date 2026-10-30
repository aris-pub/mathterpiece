// Dragging: a press goes up the tree from the shape hit to the nearest node with an attached
// on-drag listener, and that node's target (x, y or both) then moves with the pointer, in its
// parent's coordinates. A
// move where any of the listener's conditions fails is rejected.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

type Point = [number, number];

export class Drags {
  private byNode = new Map<number, Obj[]>();
  private held: { listener: Obj; node: number; grab: Point; start: Point } | null = null;

  constructor(private rt: Runtime) {
    for (const o of rt.objects) {
      if (o.kind !== "on-drag" || !o.target) continue;
      const [node] = o.target;
      this.byNode.set(node, [...(this.byNode.get(node) ?? []), o]);
    }
  }

  get dragging(): boolean {
    return this.held !== null;
  }

  /** Whether pressing object i would drag something. */
  draggable(i: number): boolean {
    return this.find(i) !== null;
  }

  private find(hit: number): { listener: Obj; node: number } | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byNode.get(i) ?? []).find((l) => this.attached(l));
      if (listener) return { listener, node: i };
    }
    return null;
  }

  private attached(listener: Obj): boolean {
    const when = listener.when;
    return when === null || when === undefined || Boolean(this.rt.eval(when, null, {}));
  }

  /** Starts dragging whatever a press on object i at a point in scene coordinates grabs. */
  grab(hit: number, scene: Point): boolean {
    const found = this.find(hit);
    if (!found) return false;
    const { node } = found;
    this.held = {
      ...found,
      grab: this.local(node, scene),
      start: [this.rt.value(node, "x"), this.rt.value(node, "y")],
    };
    return true;
  }

  /** Moves the held node by how far the pointer has gone; returns whether anything moved. */
  move(scene: Point): boolean {
    const held = this.held;
    if (!held) return false;
    const [px, py] = this.local(held.node, scene);
    const target = held.listener.target?.[1] ?? "pos";
    const x = target === "y" ? held.start[0] : held.start[0] + px - held.grab[0];
    const y = target === "x" ? held.start[1] : held.start[1] + py - held.grab[1];
    const before: Point = [this.rt.value(held.node, "x"), this.rt.value(held.node, "y")];
    this.rt.write(held.node, "x", x);
    this.rt.write(held.node, "y", y);
    const conditions = held.listener.conditions ?? [];
    if (conditions.every((c) => Boolean(this.rt.eval(c, null, {})))) return true;
    this.rt.write(held.node, "x", before[0]);
    this.rt.write(held.node, "y", before[1]);
    return false;
  }

  release(): void {
    this.held = null;
  }

  // A scene point in the coordinates the node's x and y live in.
  private local(node: number, [x, y]: Point): Point {
    return this.rt.frame(this.rt.parent(node)).inverse().apply(x, y);
  }
}
