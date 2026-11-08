// Dragging (docs/reference.md, "Dragging"): a press goes up the scene tree from the shape hit to
// the nearest shape with an on-drag whose when holds. A target that is the shape's own x, y or
// pos follows the pointer, keeping the offset it had at the press; a group moves every member, and
// a fixed-size group its translate, since its members are in screen pixels (mtp-ggs). Any other
// target is written by the drag's move: its to reads pointer, where the pointer has moved the
// shape's position, in the frame that position lives in (mtp-r6al). The listener's conditions
// clamp each write.
import { apply, compose, invert } from "./builtins.ts";
import { heardIn } from "./click.ts";
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
  // A fixed-size group, moved by its translate.
  fixed?: boolean;
  // A drag written by a move whose to reads pointer.
  mapped?: boolean;
  // Whether the pointer has moved since the press.
  moved?: boolean;
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

  /** The shape the held drag listens on, and whether the pointer has moved it since the press. */
  get shape(): number | null {
    return this.held?.shape ?? null;
  }

  get moved(): boolean {
    return this.held?.moved ?? false;
  }

  /** What the held drag writes, as "id:attr". */
  get targets(): string[] {
    if (!this.held) return [];
    if (this.held.members) return this.held.members.map(([m]) => `${m}:pos`);
    if (this.held.fixed) return [`${this.held.shape}:translate`];
    const [id, attr] = this.held.target;
    return [`${id}:${attr ?? ""}`];
  }

  /** Whether a press on shape hit, in the view given, drags anything. */
  draggable(hit: number, view?: number): boolean {
    return this.find(hit, view) !== null;
  }

  private find(hit: number, view?: number): { listener: Obj; shape: number } | null {
    for (let i: number | null = hit; i !== null; i = this.rt.parent(i)) {
      const listener = (this.byShape.get(i) ?? []).find(
        (l) => heardIn(l, view, this.rt.quiet) && (!l.active || Boolean(this.rt.evaluate(l.active as never))),
      );
      if (listener) return { listener, shape: i };
    }
    return null;
  }

  /** Starts dragging whatever a press on shape hit, at a point in scene coordinates, in the view
   * given, grabs. */
  grab(hit: number, scene: Point, view?: number): boolean {
    const found = this.find(hit, view);
    if (!found) return false;
    const { listener, shape } = found;
    const target = listener.target!;
    const own = target[0] === shape && ["x", "y", "pos"].includes(target[1] ?? "");
    const rt = this.rt;
    if (listener.map) {
      // Where the shape's position is, and the pointer, in the frame the position lives in: a
      // fixed-size group's translate in its container's, any other shape's in its own.
      const fixed = Boolean(rt.objects[shape]!["fixed-size"]);
      const start = (fixed ? rt.value(shape, "translate") : rt.value(shape, "pos")) as Point;
      const grab = fixed ? this.inFrame(rt.parent(shape), scene) : this.ownFrame(shape, scene);
      this.held = { listener, shape, target, grab, start, fixed, mapped: true };
      return true;
    }
    if (rt.objects[shape]!["fixed-size"] && own) {
      const start = rt.value(shape, "translate") as Point;
      this.held = { listener, shape, target, grab: this.inFrame(rt.parent(shape), scene), start, fixed: true };
      return true;
    }
    if (rt.objects[shape]!.kind === "group" && own) {
      const members = (rt.objects[shape]!.members ?? []).map(
        (m) => [m, rt.value(m, "pos") as Point] as [number, Point],
      );
      this.held = { listener, shape, target, grab: this.inFrame(shape, scene), start: [0, 0], members };
      return true;
    }
    // The shape's own position: the compiler gives any other target a move (mtp-r6al).
    this.held = { listener, shape, target, grab: this.ownFrame(shape, scene), start: rt.value(shape, "pos") as Point };
    return true;
  }

  /** Moves the held shape with the pointer; gives whether anything changed. */
  move(scene: Point): boolean {
    return this.rt.together(() => this.moveTo(scene));
  }

  private moveTo(scene: Point): boolean {
    const held = this.held;
    if (!held) return false;
    held.moved = true;
    const [id, attr] = held.target;
    const rt = this.rt;
    let changed = false;
    if (held.mapped) {
      const [px, py] = held.fixed ? this.inFrame(rt.parent(held.shape), scene) : this.ownFrame(held.shape, scene);
      const pointer: Point = [held.start[0] + px - held.grab[0], held.start[1] + py - held.grab[1]];
      const value = rt.evaluate(held.listener.map!, { pointer });
      if (attr === "pos" && id === held.shape) {
        const [x, y] = value as Point;
        changed = rt.write(id, "x", this.clamped(id, "x", x));
        return rt.write(id, "y", this.clamped(id, "y", y)) || changed;
      }
      return rt.write(id, attr, typeof value === "number" ? this.clamped(id, attr, value) : value);
    }
    if (held.fixed) {
      const [px, py] = this.inFrame(this.rt.parent(held.shape), scene);
      const x = attr === "y" ? held.start[0] : held.start[0] + px - held.grab[0];
      const y = attr === "x" ? held.start[1] : held.start[1] + py - held.grab[1];
      return rt.write(held.shape, "translate", [x, y]);
    }
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
    return changed;
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

  // A scene point in the frame a container's members live in.
  private inFrame(container: number | null, scene: Point): Point {
    return apply(invert(this.rt.toScene(container)), scene) as Point;
  }

  // A scene point where a shape's own x and y live: what, after its own translate and transform
  // and its containers', lands at the point.
  private ownFrame(shape: number, scene: Point): Point {
    const m = compose(this.rt.local(shape), this.rt.toScene(this.rt.parent(shape)));
    return apply(invert(m), scene) as Point;
  }
}
