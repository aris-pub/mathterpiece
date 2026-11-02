// Dragging (docs/reference.md, "Dragging"): a press goes up the scene tree from the shape hit to
// the nearest shape with an on-drag whose when holds. A target that is the shape's own x, y or
// pos follows the pointer, keeping the offset it had at the press; a group moves every member; a
// number the shape's position depends on takes the value that brings the shape closest to where
// the pointer has moved it. The listener's conditions clamp each write.
import { apply, compose, invert } from "./builtins.ts";
import type { Obj } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

type Point = [number, number];

interface Held {
  listener: Obj;
  shape: number;
  target: [number, string | null];
  // Where the pointer and the shape were at the press, in the frame the target lives in.
  grab: Point;
  start: Point;
  members?: [number, Point][];
}

export class Drags {
  private byShape = new Map<number, Obj[]>();
  private held: Held | null = null;

  constructor(private rt: Runtime) {
    for (const o of rt.objects) {
      if (o.kind === "on-drag") this.byShape.set(o.shape!, [...(this.byShape.get(o.shape!) ?? []), o]);
    }
  }

  get dragging(): boolean {
    return this.held !== null;
  }

  /** What the held drag writes, as "id:attr". */
  get targets(): string[] {
    if (!this.held) return [];
    if (this.held.members) return this.held.members.map(([m]) => `${m}:pos`);
    const [id, attr] = this.held.target;
    return [`${id}:${attr ?? ""}`];
  }

  draggable(hit: number): boolean {
    return this.find(hit) !== null;
  }

  private find(hit: number): { listener: Obj; shape: number } | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byShape.get(i) ?? []).find(
        (l) => !l.when || Boolean(this.rt.evaluate(l.when as never)),
      );
      if (listener) return { listener, shape: i };
    }
    return null;
  }

  /** Starts dragging whatever a press on shape hit, at a point in scene coordinates, grabs. */
  grab(hit: number, scene: Point): boolean {
    const found = this.find(hit);
    if (!found) return false;
    const { listener, shape } = found;
    const target = listener.target!;
    const own = target[0] === shape && ["x", "y", "pos"].includes(target[1] ?? "");
    const rt = this.rt;
    if (rt.objects[shape]!.kind === "group" && own) {
      const members = (rt.objects[shape]!.members ?? []).map(
        (m) => [m, rt.value(m, "pos") as Point] as [number, Point],
      );
      this.held = { listener, shape, target, grab: this.inFrame(shape, scene), start: [0, 0], members };
      return true;
    }
    this.held = {
      listener,
      shape,
      target,
      grab: own ? this.ownFrame(shape, scene) : scene,
      start: own ? (rt.value(shape, "pos") as Point) : this.where(shape),
    };
    return true;
  }

  /** Moves the held shape with the pointer; gives whether anything changed. */
  move(scene: Point): boolean {
    const held = this.held;
    if (!held) return false;
    const [id, attr] = held.target;
    const rt = this.rt;
    let changed = false;
    if (held.members) {
      const [px, py] = this.inFrame(held.shape, scene);
      const [dx, dy] = [px - held.grab[0], py - held.grab[1]];
      for (const [m, [x, y]] of held.members) {
        if (attr !== "y") changed = rt.write(m, "x", x + dx) || changed;
        if (attr !== "x") changed = rt.write(m, "y", y + dy) || changed;
      }
      return changed;
    }
    if (id === held.shape && ["x", "y", "pos"].includes(attr ?? "")) {
      const [px, py] = this.ownFrame(held.shape, scene);
      if (attr !== "y") changed = rt.write(id, "x", this.clamped(id, "x", held.start[0] + px - held.grab[0])) || changed;
      if (attr !== "x") changed = rt.write(id, "y", this.clamped(id, "y", held.start[1] + py - held.grab[1])) || changed;
      return changed;
    }
    const aim: Point = [held.start[0] + scene[0] - held.grab[0], held.start[1] + scene[1] - held.grab[1]];
    const before = rt.value(id, attr) as number;
    const best = this.closest(held.shape, id, attr, before, aim);
    rt.write(id, attr, before);
    return rt.write(id, attr, this.clamped(id, attr, best));
  }

  release(): void {
    this.held = null;
  }

  private clamped(id: number, attr: string | null, v: number): number {
    for (const c of this.held!.listener.conditions ?? []) {
      if (c.target[0] === id && c.target[1] === attr) v = this.rt.clamp(c, v);
    }
    return v;
  }

  // Gauss-Newton on one number: from the current value, step along the direction in which the
  // shape moves, halving steps that do not bring it closer. Starting from where it is keeps the
  // shape from jumping to another position that is as close (the far side of a circle).
  private closest(shape: number, id: number, attr: string | null, from: number, aim: Point): number {
    const at = (value: number): Point => {
      this.rt.write(id, attr, value);
      return this.where(shape);
    };
    const far = (p: Point) => (p[0] - aim[0]) ** 2 + (p[1] - aim[1]) ** 2;
    let value = from;
    let where = at(value);
    let distance = far(where);
    for (let k = 0; k < 30; k++) {
      const h = 1e-6 * Math.max(1, Math.abs(value));
      const ahead = at(value + h);
      const along: Point = [(ahead[0] - where[0]) / h, (ahead[1] - where[1]) / h];
      const speed = along[0] ** 2 + along[1] ** 2;
      if (speed < 1e-20) break;
      const step = (along[0] * (aim[0] - where[0]) + along[1] * (aim[1] - where[1])) / speed;
      let moved = false;
      for (let t = 1; t > 1e-3; t /= 2) {
        const next = at(value + t * step);
        const d = far(next);
        if (d < distance) {
          value += t * step;
          where = next;
          distance = d;
          moved = true;
          break;
        }
      }
      if (!moved || Math.abs(step) < 1e-10 * Math.max(1, Math.abs(value))) break;
    }
    return value;
  }

  // The shape's position as drawn, in scene coordinates.
  private where(shape: number): Point {
    return this.rt.read(shape, "pos", null) as Point;
  }

  // A scene point in the frame a container's members live in.
  private inFrame(container: number, scene: Point): Point {
    return apply(invert(this.rt.toScene(container)), scene) as Point;
  }

  // A scene point where a shape's own x and y live: what, after its own translate and transform
  // and its containers', lands at the point.
  private ownFrame(shape: number, scene: Point): Point {
    const m = compose(this.rt.local(shape), this.rt.toScene(this.rt.parent(shape)));
    return apply(invert(m), scene) as Point;
  }
}
