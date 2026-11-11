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

// The author, 2026-11-11: an exclusive writer always takes the lock on its targets, writes, and
// releases it, even for a write that takes no time, and releases it when the write throws.
describe("an exclusive write that takes no time", () => {
  const reader = { reader: true, exclusive: false };
  const exclusive = { reader: true, exclusive: true };
  const setup = () => new Scheduler(() => {}, () => {});

  it("holds the lock on its targets while it writes, and releases it after", () => {
    const s = setup();
    let inside: boolean | null = null;
    expect(
      s.instant(["1:x"], {}, exclusive, () => {
        inside = s.claim(["1:x"], {}, reader);
      }),
    ).toBe(true);
    expect(inside).toBe(false);
    expect(s.claim(["1:x"], {}, reader)).toBe(true);
  });

  it("locks nothing but its own targets", () => {
    const s = setup();
    let inside: boolean | null = null;
    s.instant(["1:x"], {}, exclusive, () => {
      inside = s.claim(["2:x"], {}, reader);
    });
    expect(inside).toBe(true);
  });

  it("releases the lock when the write throws", () => {
    const s = setup();
    expect(() =>
      s.instant(["1:x"], {}, exclusive, () => {
        throw new Error("the write failed");
      }),
    ).toThrow("the write failed");
    expect(s.claim(["1:x"], {}, reader)).toBe(true);
  });

  it("refuses a newcomer while it holds the lock, so the newcomer writes nothing", () => {
    const s = setup();
    let wrote = false;
    let accepted: boolean | null = null;
    s.instant(["1:x"], {}, exclusive, () => {
      accepted = s.instant(["1:pos"], {}, reader, () => {
        wrote = true;
      });
    });
    expect([accepted, wrote]).toEqual([false, false]);
  });

  it("a seek of a paused exclusive player holds the lock while it writes", () => {
    const s = setup();
    const source = {};
    let inside: boolean | null = null;
    const player = {
      targets: ["1:x"],
      done: false,
      time: 0,
      release() {},
      seek() {
        inside = s.claim(["1:x"], {}, reader);
      },
    } as unknown as Player;
    s.hold(player, source);
    expect(s.seek(source, 0.5, exclusive)).toBe(true);
    expect(inside).toBe(false);
    expect(s.claim(["1:x"], {}, reader)).toBe(true);
  });

  it("a player whose first write throws releases its targets", () => {
    const s = setup();
    const player = {
      targets: ["1:x"],
      done: false,
      time: 0,
      release() {},
      seek() {
        throw new Error("the write failed");
      },
    } as unknown as Player;
    expect(() => s.start(player, {}, exclusive)).toThrow("the write failed");
    expect(s.claim(["1:x"], {}, reader)).toBe(true);
  });
});
