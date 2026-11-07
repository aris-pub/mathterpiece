// Animations run over time or scrubbed by a slider (docs/reference.md, "Transitions and
// animations" and "Controls").
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import type { Runtime } from "../src/runtime.ts";
import { load } from "./helpers.ts";

describe("a slider's stops", () => {
  function slider() {
    const rt = load("stops");
    const a = rt.objects[rt.id("a")]!;
    return { rt, p: new Player(rt, a.animation!, a.conditions ?? []) };
  }

  it("are the values at each stop", () => {
    const { p } = slider();
    expect(p.valuesAt(4)).toEqual([0, 0.25, 0.5, 0.75, 1].map((u) => p.valueAt(u)));
    expect(p.valuesAt(4)).toEqual([0, 5, 10, 15, 20]);
  });

  it("follow a write to what a move's ends read", () => {
    const { rt, p } = slider();
    expect(p.valuesAt(2)).toEqual([0, 10, 20]);
    rt.write(rt.id("lo"), null, 4);
    expect(p.valuesAt(2)).toEqual([4, 12, 20]);
    rt.write(rt.id("hi"), null, 2);
    expect(p.valuesAt(2)).toEqual([4, 4, 4]);
    expect(p.valuesAt(4)).toEqual([4, 4, 4, 4, 4]);
  });
});

function setup(animation: string): [Runtime, Player, (name: string, attr?: string) => unknown] {
  const rt = load("anim");
  const value = (name: string, attr?: string) => rt.value(rt.id(name), attr ?? null);
  return [rt, new Player(rt, rt.id(animation)), value];
}

describe("a player", () => {
  it("runs its moves in order, each from the value of what it moves", () => {
    const [, p, v] = setup("a");
    expect(p.duration).toBe(4);
    p.seek(1);
    expect(v("k")).toBe(5);
    p.seek(2);
    expect(v("k")).toBe(10);
    expect(v("j")).toBe(0);
    p.seek(3.5);
    expect(v("j")).toBeCloseTo(1 + 2 * 0.5 ** 3);
    expect(p.done).toBe(false);
    p.seek(4);
    expect(v("j")).toBe(3);
    expect(p.done).toBe(true);
  });

  it("runs at-once steps together, for as long as the longest", () => {
    const [, p, v] = setup("both");
    expect(p.duration).toBe(2);
    p.seek(1);
    expect([v("k"), v("j")]).toEqual([5, 5]);
  });

  it("changes a bool at the start of its move", () => {
    const [, p, v] = setup("flip");
    p.seek(0);
    expect(v("on")).toBe(true);
  });

  it("changes a bool where its step-ease says", () => {
    const [, p, v] = setup("late");
    p.seek(0.5);
    expect(v("on")).toBe(false);
    p.seek(1);
    expect(v("on")).toBe(true);
  });

  it("jumps at the start of each interval of (step n)", () => {
    const [, p, v] = setup("jumps");
    p.seek(0);
    expect(v("k")).toBe(1);
    p.seek(0.5);
    expect(v("k")).toBe(3);
    p.seek(0.75);
    expect(v("k")).toBe(4);
  });

  it("mixes colors", () => {
    const [, p, v] = setup("fade");
    p.seek(0.5);
    expect(v("dot", "fill")).toBe("#808080ff");
  });

  it("moves a position along a straight line", () => {
    const [, p, v] = setup("slide");
    p.seek(0.5);
    expect(v("dot", "pos")).toEqual([1.5, 0.5]);
  });

  it("scrubs by a slider's position, each part taking a share equal to its duration", () => {
    const [, p, v] = setup("a");
    p.scrub(0.25);
    expect(v("k")).toBe(5);
    p.scrub(0);
    expect(v("k")).toBe(0);
  });

  it("lists the variables and attributes it writes", () => {
    const [rt, p] = setup("both");
    expect(p.targets).toEqual([`${rt.id("k")}:`, `${rt.id("j")}:`]);
  });

  it("plays a loop's body n times, each round from the start", () => {
    // mtp-aql: (loop n); a move with from jumps back to it each round.
    const [, p, v] = setup("thrice");
    expect(p.duration).toBe(3);
    p.seek(0.5);
    expect(v("k")).toBe(5);
    p.seek(1.25);
    expect(v("k")).toBe(2.5);
    p.seek(2.5);
    expect(v("k")).toBe(5);
    expect(p.done).toBe(false);
    p.seek(3);
    expect(v("k")).toBe(10);
    expect(p.done).toBe(true);
    p.seek(5);
    expect(v("k")).toBe(10);
  });

  it("loops forever, reading a move's ends again each round", () => {
    // A move with no from carries on from where the last round left it.
    const [, p, v] = setup("forever");
    expect(p.duration).toBe(Number.POSITIVE_INFINITY);
    p.seek(0.5);
    expect(v("j")).toBe(0.5);
    p.seek(1.5);
    expect(v("j")).toBe(1.5);
    p.seek(2.25);
    expect(v("j")).toBe(2.25);
    expect(p.done).toBe(false);
  });

  it("plays an at-once group again in every round of a loop, stepped as a play steps", () => {
    // Seen in examples/ease-race.mtp: from the second round on, the balls jumped out.
    const [, p, v] = setup("outback");
    const seen: number[] = [];
    for (let t = 0; t <= 4.5; t += 0.05) {
      p.seek(t);
      if (Math.abs(t - 2.5) < 0.026 || Math.abs(t - 4.5) < 0.026) seen.push(v("k") as number);
    }
    expect(seen.map((x) => Math.round(x * 10) / 10)).toEqual([5, 5]);
  });

  it("plays any one step alone, however its start rounds", () => {
    // Seen in examples/times-tables.mtp: the fourth step's span began at 10.600000000000001 and
    // its move at 10.6, so playing that step alone left its move out.
    const [, p, v] = setup("stops");
    p.only(3);
    const span = p.spans[3]!;
    for (let t = span.start; t <= span.end + 0.01; t += 0.05) p.seek(t);
    expect(v("k")).toBe(9);
  });

  it("gives a looping body's items as its steps, and the one running in any round", () => {
    const [, p] = setup("rounds");
    expect(p.spans).toEqual([
      { start: 0, end: 1 },
      { start: 1, end: 2 },
    ]);
    p.seek(3.5);
    expect(p.stepNow()).toBe(1);
    p.seek(4.5);
    expect(p.stepNow()).toBe(0);
  });

  it("moves an instance's fill as every member's, through a group inside it", () => {
    // mtp-4cw5: the colors mix, not counted as numbers.
    const [rt, p] = setup("recolor");
    p.seek(0.5);
    expect(rt.value(rt.id("duo.p"), "fill")).toBe("#808080ff");
    expect(rt.value(rt.id("duo.q"), "fill")).toBe("#808080ff");
  });

  it("reads the ends of moves that start together before any of them writes (mtp-lm24)", () => {
    const [, p, v] = setup("swap");
    p.seek(0);
    expect([v("left"), v("right")]).toEqual([2, 1]);
  });

  it("swaps in every round of a loop, wherever a frame falls in it", () => {
    // Frames that do not land on a round's start: each round read what the last had half written.
    const [, p, v] = setup("swaps");
    for (let t = 0; t <= 1.5; t += 0.3) p.seek(t);
    p.seek(1.5);
    expect([v("left"), v("right")]).toEqual([2, 1]);
  });

  it("starts a later move from what the moves before it left", () => {
    const [, p, v] = setup("chain");
    p.seek(0.5);
    p.seek(1.5);
    expect(v("right")).toBe(3.5);
    p.seek(2);
    expect(v("right")).toBe(5);
  });

  it("keeps the order of an in-order even when its moves take no time", () => {
    const [, p, v] = setup("instant-chain");
    p.seek(0);
    expect([v("left"), v("right")]).toEqual([5, 5]);
  });

  it("tells the page of a frame's writes once", () => {
    // three-body wrote dozens of times a frame, and the page redrew for each.
    const [rt, p] = setup("both");
    let heard = 0;
    rt.onChange(() => heard++);
    p.seek(0.5);
    expect(heard).toBe(1);
  });
});

