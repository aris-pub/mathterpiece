// A move to or from none (docs/reference.md, "Transitions and animations"). The author,
// 2026-11-06: a T|none target may be moved to or from none; anything but a color then jumps as a
// bool does, at the start unless a step-ease says when.
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import { load } from "./helpers.ts";

function setup(animation: string) {
  const rt = load("none-moves");
  return { p: new Player(rt, rt.id(animation)), v: (name: string) => rt.value(rt.id(name), null) };
}

describe("a move to or from none", () => {
  it("jumps at the start of the move", () => {
    const { p, v } = setup("gone");
    p.seek(0);
    expect(v("m")).toBeNull();
    p.seek(0.5);
    expect(v("m")).toBeNull();
  });

  it("jumps from none to its end at the start", () => {
    const { p, v } = setup("back");
    p.seek(0);
    expect(v("m")).toBe(3);
  });

  it("jumps where its step-ease says", () => {
    const { p, v } = setup("late");
    p.seek(0.5);
    expect(v("m")).toBe(2);
    p.seek(1);
    expect(v("m")).toBeNull();
  });

  it("takes a string to none as any string change", () => {
    const { p, v } = setup("hide");
    p.seek(0);
    expect(v("shown")).toBeNull();
  });
});
