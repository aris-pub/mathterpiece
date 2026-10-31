// Dragging: a press goes up the tree from the shape hit to the nearest node with an attached
// on-drag listener. That listener's target then changes so the node follows the pointer's motion:
// the node's own x, y or both directly, in its parent's coordinates, or any number its position
// depends on, by searching for the value that brings the node closest to where the pointer has
// moved it. A move where any of the listener's conditions fails is rejected.
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

type Point = [number, number];

interface Held {
  listener: Obj;
  node: number;
  target: [number, string];
  // Where the pointer and the node were at the press: in the node's parent's coordinates for a
  // position target, in scene coordinates for a number.
  grab: Point;
  start: Point;
  // Dragging a group moves each member: where each one was at the press, in the group's own
  // coordinates.
  members?: [number, Point][];
}

export class Drags {
  private byNode = new Map<number, Obj[]>();
  private held: Held | null = null;

  constructor(private rt: Runtime) {
    for (const o of rt.objects) {
      if (o.kind !== "on-drag" || o.node === undefined) continue;
      this.byNode.set(o.node, [...(this.byNode.get(o.node) ?? []), o]);
    }
  }

  get dragging(): boolean {
    return this.held !== null;
  }

  /** What the held drag writes, as "id.attr". */
  get targets(): string[] {
    if (!this.held) return [];
    if (this.held.members) return this.held.members.map(([m]) => `${m}.pos`);
    const [id, attr] = this.held.target;
    return [`${id}.${attr}`];
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
    const { listener, node } = found;
    const target = listener.target ?? [node, "pos"];
    if (this.rt.kind(node) === "group") {
      const members = (this.rt.obj(node).members ?? []).map(
        (m) => [m, [this.rt.value(m, "x") as number, this.rt.value(m, "y") as number]] as [number, Point],
      );
      this.held = { listener, node, target, grab: this.inside(node, scene), start: [0, 0], members };
      return true;
    }
    const position = target[0] === node && ["x", "y", "pos"].includes(target[1]);
    this.held = {
      listener,
      node,
      target,
      grab: position ? this.local(node, scene) : scene,
      start: position ? [this.rt.value(node, "x"), this.rt.value(node, "y")] : this.where(node),
    };
    return true;
  }

  /** Moves the held node with the pointer; returns whether anything moved. */
  move(scene: Point): boolean {
    const held = this.held;
    if (!held) return false;
    const [id, attr] = held.target;
    if (held.members) return this.moveMembers(held, attr, scene);
    const before = this.rt.value(id, attr === "pos" ? "pos" : attr);
    if (id === held.node && ["x", "y", "pos"].includes(attr)) {
      const [px, py] = this.local(held.node, scene);
      if (attr !== "y") this.rt.write(id, "x", held.start[0] + px - held.grab[0]);
      if (attr !== "x") this.rt.write(id, "y", held.start[1] + py - held.grab[1]);
    } else {
      const aim: Point = [held.start[0] + scene[0] - held.grab[0], held.start[1] + scene[1] - held.grab[1]];
      let value = this.closest(held.node, id, attr, before as number, aim);
      if (held.listener.type === "int") value = Math.round(value);
      this.rt.write(id, attr, value);
    }
    const conditions = held.listener.conditions ?? [];
    if (conditions.every((c) => Boolean(this.rt.eval(c, null, {})))) return true;
    this.rt.write(id, attr, before);
    return false;
  }

  private moveMembers(held: Held, attr: string, scene: Point): boolean {
    const members = held.members ?? [];
    const before = members.map(([m]) => [this.rt.value(m, "x"), this.rt.value(m, "y")]);
    const [px, py] = this.inside(held.node, scene);
    const [dx, dy] = [px - held.grab[0], py - held.grab[1]];
    for (const [m, [x, y]] of members) {
      if (attr !== "y") this.rt.write(m, "x", x + dx);
      if (attr !== "x") this.rt.write(m, "y", y + dy);
    }
    const conditions = held.listener.conditions ?? [];
    if (conditions.every((c) => Boolean(this.rt.eval(c, null, {})))) return true;
    members.forEach(([m], k) => {
      this.rt.write(m, "x", before[k]![0]);
      this.rt.write(m, "y", before[k]![1]);
    });
    return false;
  }

  release(): void {
    this.held = null;
  }

  // Gauss-Newton on one number: from the current value, step along the direction in which the
  // node moves, halving steps that do not bring it closer. Starting from where it is keeps the
  // node from jumping to another place that is as close (the far side of a circle, say).
  private closest(node: number, id: number, attr: string, from: number, aim: Point): number {
    const at = (value: number): Point => {
      this.rt.write(id, attr, value);
      return this.where(node);
    };
    const far = (p: Point) => (p[0] - aim[0]) ** 2 + (p[1] - aim[1]) ** 2;
    let value = from;
    let place = at(value);
    let distance = far(place);
    for (let k = 0; k < 30; k++) {
      const h = 1e-6 * Math.max(1, Math.abs(value));
      const ahead = at(value + h);
      const along: Point = [(ahead[0] - place[0]) / h, (ahead[1] - place[1]) / h];
      const speed = along[0] ** 2 + along[1] ** 2;
      if (speed < 1e-20) break;
      const step = (along[0] * (aim[0] - place[0]) + along[1] * (aim[1] - place[1])) / speed;
      let moved = false;
      for (let t = 1; t > 1e-3; t /= 2) {
        const next = at(value + t * step);
        const d = far(next);
        if (d < distance) {
          value += t * step;
          place = next;
          distance = d;
          moved = true;
          break;
        }
      }
      if (!moved || Math.abs(step) < 1e-10 * Math.max(1, Math.abs(value))) break;
    }
    return value;
  }

  // The node's position in scene coordinates.
  private where(node: number): Point {
    const [x = 0, y = 0] = this.rt.point(node);
    return [x, y];
  }

  // A scene point in a container's own coordinates, where its members' x and y live.
  private inside(container: number, [x, y]: Point): Point {
    return this.rt.frame(container).inverse().apply(x, y);
  }

  // A scene point in the coordinates the node's x and y live in.
  private local(node: number, [x, y]: Point): Point {
    return this.rt.frame(this.rt.parent(node)).inverse().apply(x, y);
  }
}
