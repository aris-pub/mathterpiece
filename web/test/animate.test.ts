import { describe, expect, it } from "vitest";
import { Scheduler } from "../src/animate.ts";
import type { Doc, Obj } from "../src/doc.ts";
import { Player } from "../src/player.ts";
import { Runtime } from "../src/runtime.ts";

const pair = (id: number, to: number, duration: number) => ["pair", [[id, "value"]], "number", ["transition", { to, duration }]];

// k (0) and j (1) are reals. a (2) moves k, b (3) moves j, both (4) moves both.
function world() {
  const objects: Omit<Obj, "id">[] = [
    { kind: "real", name: "k", attrs: { value: 0 } },
    { kind: "real", name: "j", attrs: { value: 0 } },
    { kind: "animation", name: "a", attrs: {}, body: pair(0, 10, 2) },
    { kind: "animation", name: "b", attrs: {}, body: pair(1, 10, 2) },
    { kind: "animation", name: "both", attrs: {}, body: ["at-once", {}, pair(0, 20, 2), pair(1, 20, 2)] },
  ];
  const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
  const rt = new Runtime(doc);
  let redraws = 0;
  const scheduler = new Scheduler(rt, () => redraws++, () => {});
  return { rt, scheduler, k: () => rt.value(0, "value"), j: () => rt.value(1, "value"), redraws: () => redraws };
}

describe("the scheduler", () => {
  it("runs a player by the clock and stops when it is done", () => {
    const w = world();
    const source = {};
    w.scheduler.start(new Player(w.rt, 2), source);
    w.scheduler.tick(1);
    expect(w.k()).toBe(5);
    w.scheduler.tick(5);
    expect(w.k()).toBe(10);
    expect(w.scheduler.busy()).toBe(false);
    expect(w.redraws()).toBeGreaterThan(1);
  });

  it("runs sources that share no target together", () => {
    const w = world();
    w.scheduler.start(new Player(w.rt, 2), {});
    w.scheduler.start(new Player(w.rt, 3), {});
    w.scheduler.tick(1);
    expect([w.k(), w.j()]).toEqual([5, 5]);
  });

  it("cancels the whole earlier source when a new one writes any of its targets", () => {
    const w = world();
    w.scheduler.start(new Player(w.rt, 4), {});
    w.scheduler.tick(1);
    w.scheduler.start(new Player(w.rt, 2), {});
    w.scheduler.tick(1);
    expect(w.j()).toBe(10);
    expect(w.k()).toBeCloseTo(10 + 0);
  });

  it("lets a slider, a drag or a toggle claim targets, cancelling what writes them", () => {
    const w = world();
    w.scheduler.start(new Player(w.rt, 4), {});
    w.scheduler.tick(1);
    w.scheduler.claim(["1.value"], {});
    w.scheduler.tick(1);
    expect([w.k(), w.j()]).toEqual([10, 10]);
    expect(w.scheduler.busy()).toBe(false);
  });

  it("pauses and resumes a source where it was", () => {
    const w = world();
    const source = {};
    w.scheduler.start(new Player(w.rt, 2), source);
    w.scheduler.tick(1);
    w.scheduler.pause(source);
    w.scheduler.tick(5);
    expect(w.k()).toBe(5);
    expect(w.scheduler.running(source)).toBe(false);
    w.scheduler.resume(source);
    w.scheduler.tick(0.5);
    expect(w.k()).toBe(7.5);
  });
});
