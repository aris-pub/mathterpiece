// A use of a choreo given a shape declared T|none plays as the inline move does (mtp-0eha). A
// move reads its start when it starts: while the shape does not exist that start is none, so the
// move jumps to its end at once (docs/reference.md, "Transitions and animations").
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import { load } from "./helpers.ts";

function run(show: boolean) {
  const rt = load("choreo-absent");
  rt.write(rt.id("show"), null, show);
  const inline = new Player(rt, rt.id("inline"));
  const used = new Player(rt, rt.id("used"));
  const opacity = (name: string) => rt.value(rt.id(name), "opacity");
  const seen: unknown[][] = [];
  for (const t of [0, 0.5, 1]) {
    inline.seek(t);
    used.seek(t);
    seen.push([opacity("a"), opacity("b")]);
  }
  rt.write(rt.id("show"), null, true);
  seen.push([opacity("a"), opacity("b")]);
  return seen;
}

describe("a use of a choreo given a shape that may not exist", () => {
  it("moves the shape as the inline move does while it exists", () => {
    expect(run(true)).toEqual([
      [1, 1],
      [0.5, 0.5],
      [0, 0],
      [0, 0],
    ]);
  });

  it("moves the shape as the inline move does while it does not exist", () => {
    expect(run(false)).toEqual([
      [null, null],
      [null, null],
      [null, null],
      [0, 0],
    ]);
  });
});
