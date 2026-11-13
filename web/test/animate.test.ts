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
    s.start(fake(() => s, () => true), {}, { reader: true });
    s.tick(0.1);
    expect(redraws()).toBe(0);
  });

  it("tells them of a frame that wrote nothing, as time still moved", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => false), {}, { reader: true });
    expect(redraws()).toBe(1);
    s.tick(0.1);
    expect(redraws()).toBe(2);
  });

  it("tells them when a player ends after its last writes", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => true, 0.05), {}, { reader: true });
    s.tick(0.1);
    expect(redraws()).toBe(1);
    expect(s.busy()).toBe(false);
  });

  it("tells them when a later player writes nothing after an earlier one wrote", () => {
    const { s, redraws } = setup();
    s.start(fake(() => s, () => true), {}, { reader: true });
    s.start(fake(() => s, () => false), {}, { reader: true });
    const before = redraws();
    s.tick(0.1);
    expect(redraws()).toBe(before + 1);
  });
});

// The rule for every write (docs/concurrency-model.md, the author, 2026-11-13): each free value
// has at most one owner. A write is accepted when its writer's priority is higher than the
// owner's, or the same and its writer was triggered later. Then the writer owns the value, and
// the owner before is cancelled on every value. A rejected write cancels nothing, and its writer
// writes that value no more.
describe("the rule for every write", () => {
  const page = { reader: false };
  const reader = { reader: true };
  const gesture = { reader: true, held: true };
  const setup = () => new Scheduler(() => {}, () => {});
  type How = { reader: boolean; held?: boolean; priority?: number };
  const write = (s: Scheduler, how: How, k: string, source: object = {}) => {
    let accepted = false;
    s.instant(source, how, () => {
      accepted = s.accept(k);
    });
    return accepted;
  };
  // A writer that runs until it ends or is cancelled. At its start it writes the keys given; then
  // each frame it writes the keys it is told to, once.
  function playing(s: Scheduler, how: How, keys: string[]) {
    let next: string[] | null = keys;
    const w = {
      accepted: [] as boolean[],
      // Writes keys on the next frame, as the writer it is, and gives what was accepted.
      writes(more: string[]) {
        next = more;
        s.tick(0.01);
        return w.accepted;
      },
    };
    const player = {
      targets: [],
      done: false,
      time: 0,
      release() {},
      seek() {
        if (next === null) return;
        w.accepted = next.map((k) => s.accept(k));
        next = null;
      },
    } as unknown as Player;
    s.start(player, w, how);
    return w;
  }

  it("accepts a write made with no writer, and gives it no owner", () => {
    const s = setup();
    expect(s.accept("1:x")).toBe(true);
    expect(s.ownerOf("1:x")).toBe(null);
  });

  it("gives a value to the writer triggered later at the same priority, cancelling the one before", () => {
    const s = setup();
    const first = playing(s, reader, ["1:x"]);
    expect(s.ownerOf("1:x")).toBe(first);
    const second = playing(s, reader, ["1:x"]);
    expect(s.ownerOf("1:x")).toBe(second);
    expect(s.running(first)).toBe(false);
  });

  // The author, 2026-11-13: a toggle flipped after a play was pressed keeps its bool.
  it("at the same priority, rejects the write of a writer triggered before the owner", () => {
    const s = setup();
    const early = playing(s, reader, []);
    const later = playing(s, reader, ["1:x"]);
    expect(later.accepted).toEqual([true]);
    expect(early.writes(["1:x"])).toEqual([false]);
    expect(s.ownerOf("1:x")).toBe(later);
  });

  it("rejects a page writer's write of a value the reader's writer owns, and cancels nothing", () => {
    const s = setup();
    const mine = playing(s, reader, ["1:x"]);
    expect(write(s, page, "1:x")).toBe(false);
    expect(s.ownerOf("1:x")).toBe(mine);
    expect(s.running(mine)).toBe(true);
  });

  it("accepts the reader's write of a value a page writer owns, and cancels it", () => {
    const s = setup();
    const theirs = playing(s, page, ["1:x"]);
    expect(write(s, reader, "1:x")).toBe(true);
    expect(s.running(theirs)).toBe(false);
  });

  it("rejects the reader's write of a value a gesture owns", () => {
    const s = setup();
    const held = { cancelled: false };
    s.grip(held, reader, () => (held.cancelled = true));
    expect(write(s, reader, "1:x", held)).toBe(true);
    expect(write(s, reader, "1:x")).toBe(false);
    expect(held.cancelled).toBe(false);
  });

  it("takes a writer's own (priority n) over its kind's", () => {
    const s = setup();
    playing(s, { reader: true, priority: 900 }, ["1:x"]);
    expect(write(s, gesture, "1:x")).toBe(false);
    expect(write(s, { reader: false, priority: 900 }, "1:x")).toBe(true);
  });

  it("decides each value on its own: a writer rejected on one is accepted on another", () => {
    const s = setup();
    const mine = playing(s, reader, ["1:x"]);
    const theirs = playing(s, page, ["1:x", "2:x"]);
    expect(theirs.accepted).toEqual([false, true]);
    expect(s.ownerOf("1:x")).toBe(mine);
    expect(s.ownerOf("2:x")).toBe(theirs);
  });

  it("stops a writer writing a value it was rejected on, for the rest of its effect", () => {
    const s = setup();
    const owner = {};
    s.grip(owner, reader, () => {});
    write(s, reader, "1:x", owner);
    const theirs = playing(s, reader, ["1:x", "2:x"]);
    expect(theirs.accepted).toEqual([false, true]);
    s.letGo(owner);
    expect(theirs.writes(["1:x", "2:x"])).toEqual([false, true]);
    expect(s.ownerOf("1:x")).toBe(null);
  });

  it("writes the value again on a new trigger of the same writer", () => {
    const s = setup();
    const owner = {};
    s.grip(owner, reader, () => {});
    write(s, reader, "1:x", owner);
    const theirs = playing(s, reader, ["1:x"]);
    expect(theirs.accepted).toEqual([false]);
    s.letGo(owner);
    s.resume(theirs, reader);
    expect(theirs.writes(["1:x"])).toEqual([true]);
  });

  it("cancels a writer that loses one value on every value it owned", () => {
    const s = setup();
    const theirs = playing(s, page, ["1:x", "2:x"]);
    write(s, reader, "1:x");
    expect([s.ownerOf("1:x") === theirs, s.ownerOf("2:x")]).toEqual([false, null]);
  });

  it("never cancels a writer by its own write", () => {
    const s = setup();
    const mine = { cancelled: false };
    s.grip(mine, reader, () => (mine.cancelled = true));
    write(s, reader, "1:x", mine);
    expect(write(s, reader, "1:x", mine)).toBe(true);
    expect(mine.cancelled).toBe(false);
  });

  it("gives a paused writer nothing to own", () => {
    const s = setup();
    const mine = playing(s, reader, ["1:x"]);
    s.pause(mine);
    expect(s.ownerOf("1:x")).toBe(null);
    expect(write(s, page, "1:x")).toBe(true);
  });

  it("gives a write that takes no time its value only while it writes", () => {
    const s = setup();
    let inside: boolean | null = null;
    s.instant({}, { reader: true, priority: 900 }, () => {
      s.accept("1:x");
      inside = write(s, reader, "1:x");
    });
    expect(inside).toBe(false);
    expect(write(s, page, "1:x")).toBe(true);
  });

  it("releases what a writer owned when its write throws", () => {
    const s = setup();
    expect(() =>
      s.instant({}, reader, () => {
        s.accept("1:x");
        throw new Error("the write failed");
      }),
    ).toThrow("the write failed");
    expect(s.ownerOf("1:x")).toBe(null);
  });

  it("releases what a writer owned when it is let go", () => {
    const s = setup();
    const held = {};
    s.grip(held, reader, () => {});
    write(s, reader, "1:x", held);
    s.letGo(held);
    expect(s.ownerOf("1:x")).toBe(null);
  });
});
