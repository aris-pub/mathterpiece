// Animations run over time or scrubbed by a slider (docs/reference.md, "Transitions and
// animations" and "Controls").
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import type { Runtime } from "../src/runtime.ts";
import { load } from "./helpers.ts";

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
});

