// Animations run over time or scrubbed by a slider (docs/reference.md, "Transitions and
// animations" and "Controls").
import { describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { Player } from "../src/player.ts";
import { Runtime } from "../src/runtime.ts";

const docs = import.meta.glob("./data/runtime/*.mtpc", { query: "?raw", import: "default", eager: true });

function setup(animation: string): [Runtime, Player, (name: string, attr?: string) => unknown] {
  const rt = new Runtime(JSON.parse(docs["./data/runtime/anim.mtpc"] as string) as Doc);
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
});
