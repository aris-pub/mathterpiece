// The scheduler tells the page's views of each frame once: a frame whose writes the views have
// heard of already is not told again.
import { describe, expect, it } from "vitest";
import { Scheduler } from "../src/animate.ts";
import type { Player } from "../src/player.ts";

// A player that, when it seeks, writes (and so the page tells its views) or not, and is done
// after a given time.
function fake(scheduler: () => Scheduler, writes: () => boolean, end = 10): Player {
  const p = {
    targets: [] as string[],
    done: false,
    release() {},
    seek(t: number) {
      p.done = t >= end;
      if (writes()) scheduler().told();
    },
  };
  return p as unknown as Player;
}

describe("telling the views of a frame", () => {
  function setup() {
    let redraws = 0;
    const s = new Scheduler(
      () => {
        redraws++;
        s.told();
      },
      () => {},
    );
    return { s, redraws: () => redraws };
  }

  it("does not tell them again of a frame whose writes they heard of", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => true), {}, { reader: true, exclusive: false });
    s.tick(0.1);
    expect(redraws()).toBe(0);
  });

  it("tells them of a frame that wrote nothing, as time still moved", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => false), {}, { reader: true, exclusive: false });
    expect(redraws()).toBe(1);
    s.tick(0.1);
    expect(redraws()).toBe(2);
  });

  it("tells them when a player ends after its last writes", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => true, 0.05), {}, { reader: true, exclusive: false });
    s.tick(0.1);
    expect(redraws()).toBe(1);
    expect(s.busy()).toBe(false);
  });

  it("tells them when a later player writes nothing after an earlier one wrote", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => true), {}, { reader: true, exclusive: false });
    s.start(fake(() => s, () => false), {}, { reader: true, exclusive: false });
    const before = redraws();
    s.tick(0.1);
    expect(redraws()).toBe(before + 1);
  });
});
