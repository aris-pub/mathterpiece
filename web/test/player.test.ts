import { describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { Player } from "../src/player.ts";
import { Runtime } from "../src/runtime.ts";

const tr = (spec: Record<string, unknown>) => ["transition", spec];
const pair = (target: [number, string], kind: string, spec: Record<string, unknown>) => ["pair", [target], kind, tr(spec)];

// k (0) and j (1) are reals, c (2) a circle, t (3) a text; animations from 4 on.
function world(...bodies: unknown[]) {
  const objects: Omit<Obj, "id">[] = [
    { kind: "real", name: "k", attrs: { value: 0 } },
    { kind: "real", name: "j", attrs: { value: 10 } },
    { kind: "circle", name: "c", attrs: { x: 0, y: 0, fill: "#000000ff", transform: [1, 0, 0, 0, 1, 0] } },
    { kind: "text", name: "t", attrs: { value: "a" } },
    ...bodies.map((body, k) => ({ kind: "animation", name: `a${k}`, attrs: {}, body })),
  ];
  const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
  const rt = new Runtime(doc);
  return { rt, player: (k = 0) => new Player(rt, 4 + k) };
}
const K: [number, string] = [0, "value"];
const J: [number, string] = [1, "value"];

describe("running by time", () => {
  it("runs a pair from where its target is", () => {
    const { rt, player } = world(pair(K, "number", { to: 10, duration: 2 }));
    const p = player();
    expect(p.duration).toBe(2);
    p.seek(1);
    expect(rt.value(0, "value")).toBe(5);
    p.seek(2);
    expect(rt.value(0, "value")).toBe(10);
    expect(p.done).toBe(true);
  });

  it("starts each step of an in-order from where the step before left things", () => {
    const { rt, player } = world([
      "in-order",
      {},
      pair(K, "number", { to: 10, duration: 1 }),
      ["wait", 1],
      pair(K, "number", { to: 0, duration: 2 }),
    ]);
    const p = player();
    expect(p.duration).toBe(4);
    p.seek(1.5);
    expect(rt.value(0, "value")).toBe(10);
    p.seek(3);
    expect(rt.value(0, "value")).toBe(5);
  });

  it("runs an at-once together, each pair for its own duration", () => {
    const { rt, player } = world(["at-once", {}, pair(K, "number", { to: 10, duration: 2 }), pair(J, "number", { to: 0, duration: 1 })]);
    const p = player();
    expect(p.duration).toBe(2);
    p.seek(1);
    expect([rt.value(0, "value"), rt.value(1, "value")]).toEqual([5, 0]);
  });

  it("fills in default durations and eases", () => {
    const { rt, player } = world(["at-once", { "default-duration": 2, "default-ease": "ease-in" }, pair(K, "number", { to: 8 })]);
    player().seek(1);
    expect(rt.value(0, "value")).toBeCloseTo(1);
  });

  it("warps time across a whole in-order with its own ease", () => {
    const { rt, player } = world(["in-order", { ease: "ease-in" }, pair(K, "number", { to: 1, duration: 1 }), pair(K, "number", { to: 2, duration: 1 })]);
    player().seek(1);
    expect(rt.value(0, "value")).toBeCloseTo(0.25);
  });

  it("evaluates ends that read the scene when their step starts", () => {
    const { rt, player } = world([
      "in-order",
      {},
      pair(J, "number", { to: 20, duration: 1 }),
      pair(K, "number", { to: ["read", 1, "value"], duration: 1 }),
    ]);
    const p = player();
    p.seek(2);
    expect(rt.value(0, "value")).toBe(20);
  });

  it("writes every member of a distributed target, each from its own start", () => {
    const { rt, player } = world(["pair", [K, J], "number", tr({ to: 20, duration: 2 })]);
    player().seek(1);
    expect([rt.value(0, "value"), rt.value(1, "value")]).toEqual([10, 15]);
  });

  it("crossfades text through the runtime's morphs", () => {
    const { rt, player } = world(pair([3, "value"], "text", { to: "b", duration: 2 }));
    const p = player();
    p.seek(1);
    expect(rt.value(3, "value")).toBe("b");
    expect(rt.morphs.get(3)).toEqual(["a", 0.5]);
    p.seek(2);
    expect(rt.morphs.size).toBe(0);
  });

  it("follows a named animation inside another", () => {
    const { rt, player } = world(pair(K, "number", { to: 10, duration: 1 }), ["in-order", {}, ["animation", 4], ["wait", 1]]);
    const p = player(1);
    expect(p.duration).toBe(2);
    p.seek(1);
    expect(rt.value(0, "value")).toBe(10);
  });
});

describe("steps and jumping", () => {
  const tour = [
    "in-order",
    {},
    pair(K, "number", { to: 10, duration: 1 }),
    ["wait", 1],
    pair(K, "number", { to: 20, duration: 1 }),
    ["wait", 1],
    pair(J, "number", { to: 0, duration: 1 }),
  ];

  it("knows the steps of its top-level in-order, leaving out waits", () => {
    const { player } = world(tour);
    expect(player().steps.map((s) => s.start)).toEqual([0, 2, 4]);
  });

  it("jumps to a step, which starts from wherever things are", () => {
    const { rt, player } = world(tour);
    const p = player();
    p.seek(0.5);
    p.jump(1);
    p.seek(2.5);
    expect(rt.value(0, "value")).toBeCloseTo(12.5);
  });

  it("runs one step alone, and nothing after it", () => {
    const { rt, player } = world(tour);
    const p = player();
    p.only(1);
    p.seek(10);
    expect([rt.value(0, "value"), rt.value(1, "value")]).toEqual([20, 10]);
    expect(p.done).toBe(true);
  });

  it("knows when a step holds", () => {
    const { rt, player } = world(tour);
    const p = player();
    expect(p.holds(0)).toBe(false);
    rt.write(0, "value", 10);
    expect(p.holds(0)).toBe(true);
  });
});

describe("scrubbed by progress", () => {
  it("maps the track onto the animation, durations as shares", () => {
    const { rt, player } = world(["in-order", {}, pair(K, "number", { from: 0, to: 10, duration: 3 }), pair(K, "number", { to: 20, duration: 1 })]);
    const p = player();
    p.scrub(0.5);
    expect(rt.value(0, "value")).toBeCloseTo(20 / 3);
    p.scrub(0.875);
    expect(rt.value(0, "value")).toBeCloseTo(15);
  });

  it("finds where the knob belongs for one target", () => {
    const { rt, player } = world(pair(K, "number", { from: 0, to: 360 }));
    rt.write(0, "value", 90);
    expect(player().knob()).toBeCloseTo(0.25, 3);
  });

  it("has no single place for the knob with several targets", () => {
    const { player } = world(["at-once", {}, pair(K, "number", { from: 0, to: 1 }), pair(J, "number", { from: 0, to: 1 })]);
    expect(player().knob()).toBeNull();
  });

  it("lists its targets", () => {
    const { player } = world(["at-once", {}, pair(K, "number", { to: 1, duration: 1 }), pair([2, "pos"], "point", { to: [1, 1], duration: 1 })]);
    expect(player().targets).toEqual(["0.value", "2.pos"]);
  });
});

describe("parts that start together", () => {
  // j's end reads k: 99 if k is already 1, else 5. k's part writes 1 at once.
  const setK = pair(K, "number", { to: 1, duration: 0 });
  const setJ = pair(J, "number", { to: ["if", ["=", ["read", 0, "value"], 1], 99, 5], duration: 0 });

  it.each([
    ["k first", [setK, setJ]],
    ["j first", [setJ, setK]],
  ])("read the scene as it was when they started (%s)", (_, parts) => {
    const { rt, player } = world(["at-once", {}, ...parts]);
    player().seek(0);
    expect(rt.value(1, "value")).toBe(5);
    expect(rt.value(0, "value")).toBe(1);
  });

  it("while a later step of an in-order sees what the step before wrote, even at the same instant", () => {
    const { rt, player } = world(["in-order", {}, setK, setJ]);
    player().seek(0);
    expect(rt.value(1, "value")).toBe(99);
  });

  it("and so does a step after an at-once", () => {
    const { rt, player } = world(["in-order", {}, ["at-once", {}, setK, pair(J, "number", { to: 3, duration: 0 })], setJ]);
    player().seek(0);
    expect(rt.value(1, "value")).toBe(99);
  });
});

describe("an animation that is another animation's name", () => {
  it("has the steps of the one it names", () => {
    const steps = ["in-order", {}, pair(K, "number", { to: 1, duration: 1 }), pair(J, "number", { to: 2, duration: 1 })];
    const { player } = world(steps, ["animation", 4]);
    expect(player(0).steps.length).toBe(2);
    expect(player(1).steps.length).toBe(2);
  });
});
