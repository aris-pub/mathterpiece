// Runs the animations writers set off, and decides every write a writer makes, as
// docs/concurrency-model.md says (the author, 2026-11-13). Each free value written, a target,
// has at most one owner: the running writer whose write it last accepted. A write is accepted
// when its writer's priority is higher than the owner's, or the same and its writer was triggered
// later. Then the writer becomes the owner, and the writer that owned the value before is
// cancelled on every value. A rejected write cancels nothing, and its writer writes that value no
// more for the rest of its effect. Each value is decided on its own. Time is in seconds; the page
// moves it forward on each frame.
import type { Player } from "./player.ts";

// The priorities writers have when they give none: the page's (on-view, on-ready), the reader's,
// and a gesture's (on-drag, a held slider's knob, on-pointermove).
export const PAGE = 300;
export const READER = 500;
export const GESTURE = 700;
// An on-view's: nothing the reader does cuts it short (the author, 2026-11-13).
export const VIEW = 1000;

/** Who set a writer off, the reader or not (on-view), whether it is a gesture the reader is
 * making now (a dragged shape, a slider's knob held, a pointer moving), and its own (priority n),
 * if it gives one. */
export interface How {
  reader: boolean;
  priority?: number | undefined;
  held?: boolean;
}

interface Running {
  source: object;
  // A drag and a slider's knob have no player: they write as the pointer moves.
  player: Player | null;
  time: number;
  paused: boolean;
  // Where it pauses by itself: a stepper plays one step and stops at its end.
  until?: number | undefined;
  how: How;
  // Told when another writer cancels it: a drag then stops following the pointer.
  cancelled?: () => void;
  // A drag along a play's bars: a gesture that moves its player where the pointer is, not with
  // the clock.
  scrubbing?: boolean;
  // When it was triggered, counted: at the same priority, the one triggered later wins.
  born: number;
  // The values a write of it was rejected on: it writes them no more.
  blocked: Set<string>;
}

function priority(how: How): number {
  return how.priority ?? (how.held ? GESTURE : how.reader ? READER : PAGE);
}

export class Scheduler {
  private sources: Running[] = [];
  // Each target's owner, by the runtime's key of the free value ("id:attr").
  private owners = new Map<string, Running>();
  // The writer whose writes are being made now, if any: a write made with none, such as a
  // control writing its own step, is not decided.
  private current: Running | null = null;
  private rejected = 0;
  // Paused plays and steppers, told of every accepted write of what they move by another writer.
  private watchers: { source: object; reached: Set<string>; written: () => void }[] = [];
  // What moves a view's own state, such as a canvas fading something in: it writes nothing in
  // the model, so it never collides with a writer.
  private tickers: ((seconds: number) => boolean)[] = [];
  // Whether the page has told its views of a change since this last changed what it runs.
  private heard = false;

  /** wake is called whenever something starts moving, so the page can ask for frames; reach
   * gives the free values a write of a target ("id:attr") writes, for the watchers. */
  constructor(
    private redraw: () => void,
    private wake: () => void,
    private reach: (target: string) => string[] = (t) => [t],
  ) {}

  /** The page calls this whenever it tells its views of a change. */
  told(): void {
    this.heard = true;
  }

  busy(): boolean {
    return this.tickers.length > 0 || this.sources.some((s) => s.player && !s.paused && !s.scrubbing);
  }

  /** Moves view state with the clock; tick gives whether it has more to do. */
  addTicker(tick: (seconds: number) => boolean): void {
    this.tickers.push(tick);
    this.wake();
  }

  running(source: object): boolean {
    return this.sources.some((s) => s.source === source && !s.paused && !s.scrubbing);
  }

  playerOf(source: object): Player | null {
    return this.sources.find((s) => s.source === source)?.player ?? null;
  }

  /** The player of a source that is paused, or null. */
  pausedOf(source: object): Player | null {
    return this.sources.find((s) => s.source === source && s.paused)?.player ?? null;
  }

  /** Whether any writer runs, as an on-view or an on-ready does, from the given source. */
  runs(source: object): boolean {
    return this.sources.some((s) => s.source === source && !s.paused);
  }

  /**
   * Decides a write of the free value k by the writer making writes now, as the runtime asks
   * before it writes one that changes something; gives whether it is accepted.
   */
  accept(k: string): boolean {
    const by = this.current;
    if (!by) return true;
    const owner = this.owners.get(k);
    const loses = (o: Running) => {
      const [p, q] = [priority(by.how), priority(o.how)];
      return p < q || (p === q && by.born < o.born);
    };
    if (by.blocked.has(k) || (owner && owner.source !== by.source && loses(owner))) {
      by.blocked.add(k);
      this.rejected++;
      return false;
    }
    if (owner && owner.source !== by.source) this.cancel(owner);
    this.owners.set(k, by);
    const reaches = (r: string) => k === r || k.startsWith(`${r}.`);
    for (const w of [...this.watchers]) if (w.source !== by.source && [...w.reached].some(reaches)) w.written();
    return true;
  }

  private triggers = 0;
  private entry(source: object, player: Player | null, how: How, time = 0): Running {
    return { source, player, time, paused: false, how, born: ++this.triggers, blocked: new Set() };
  }

  private cancel(s: Running): void {
    this.forget(s.source);
    s.cancelled?.();
  }

  /** Starts a player for a source, from the time from, and pauses it at until when given.
   * reset, when given, writes first, as part of the same effect. Every start is made: a write it
   * makes may be rejected, but the writer is not. */
  start(player: Player, source: object, how: How, from = 0, reset?: () => void, until?: number): boolean {
    this.forget(source);
    player.release();
    this.run(player, source, how, from, reset, until);
    return true;
  }

  /**
   * A drag along a play's bars (the author, 2026-11-13): a gesture, triggered now, that moves
   * its player to where the pointer is with scrubTo, and owns what it writes until it is paused
   * or let go. cancelled is called if another writer cancels it.
   */
  scrub(player: Player, source: object, how: How, cancelled: () => void): void {
    this.forget(source);
    player.release();
    this.sources.push({ ...this.entry(source, player, { ...how, held: true }), scrubbing: true, cancelled });
  }

  /** Moves a scrubbing source's player to a time. reset, when given, writes first. Gives false
   * when the source no longer scrubs. */
  scrubTo(source: object, time: number, reset?: () => void): boolean {
    const s = this.sources.find((r) => r.source === source && r.scrubbing);
    if (!s?.player) return false;
    s.time = time;
    this.heard = false;
    const player = s.player;
    this.as(s, () => {
      reset?.();
      player.seek(time);
    });
    if (!this.heard) this.redraw();
    return true;
  }

  /** Tells written of every accepted write by another source of a free value these targets
   * reach. */
  watch(source: object, targets: string[], written: () => void): void {
    this.watchers = this.watchers.filter((w) => w.source !== source);
    this.watchers.push({ source, reached: new Set(targets.flatMap((t) => this.reach(t))), written });
  }

  unwatch(source: object): void {
    this.watchers = this.watchers.filter((w) => w.source !== source);
  }

  private run(player: Player, source: object, how: How, from: number, reset?: () => void, until?: number): void {
    const s = this.entry(source, player, how, from);
    s.until = until;
    this.sources.push(s);
    // A seek that writes something tells the views already, as they stand now.
    this.heard = false;
    this.as(s, () => {
      reset?.();
      player.seek(from);
    });
    if (!this.heard) this.redraw();
    this.wake();
  }

  // Makes s's writes, deciding each. A writer that throws while it writes is forgotten, and a
  // paused one owns nothing after.
  private as(s: Running, write: () => void): void {
    const was = this.current;
    this.current = s;
    try {
      write();
    } catch (err) {
      this.forget(s.source);
      throw err;
    } finally {
      this.current = was;
      if (s.paused) this.release(s);
    }
  }

  /**
   * A write that takes no time, such as a slider's step, an on-pointermove's write, a toggle's
   * flip or a held drag's move: the writer runs while it writes, and a held one until its release.
   * Gives false when a write of it was rejected.
   */
  instant(source: object, how: How, write: () => void): boolean {
    const held = this.sources.find((r) => r.source === source && !r.player);
    const s = held ?? this.entry(source, null, how);
    if (held) held.how = { ...how, held: Boolean(held.how.held || how.held) };
    else this.sources.push(s);
    const before = this.rejected;
    try {
      this.as(s, write);
    } finally {
      if (!held) this.forget(s);
    }
    return this.rejected === before;
  }

  /** A drag or a slider's knob the reader holds: a running writer, held, until the release, which
   * owns what its accepted writes write. cancelled is called if another writer cancels it. */
  grip(source: object, how: How, cancelled: () => void): void {
    this.forget(source);
    this.sources.push({ ...this.entry(source, null, { ...how, held: true }), cancelled });
  }

  /** Ends a source without cancelling it, as a drag's release does. */
  letGo(source: object): void {
    this.forget(source);
  }

  /** A paused source writes nothing, so it owns nothing. A scrubbing one stops scrubbing. */
  pause(source: object): void {
    for (const s of this.sources) {
      if (s.source !== source) continue;
      s.paused = true;
      s.scrubbing = false;
      this.release(s);
    }
  }

  /** Plays a source's player on from where it stands, to the time until when given. */
  resume(source: object, how: How, until?: number): boolean {
    const s = this.sources.find((r) => r.source === source);
    if (!s?.player) return false;
    s.how = how;
    s.born = ++this.triggers;
    s.blocked.clear();
    s.paused = false;
    s.until = until;
    this.wake();
    return true;
  }

  tick(seconds: number): void {
    this.tickers = this.tickers.filter((t) => t(seconds));
    this.heard = false;
    for (const s of [...this.sources]) {
      if (s.paused || s.scrubbing || !s.player || !this.sources.includes(s)) continue;
      s.time += seconds;
      if (s.until !== undefined && s.time >= s.until) {
        s.time = s.until;
        s.paused = true;
        s.until = undefined;
      }
      this.heard = false;
      const player = s.player;
      this.as(s, () => player.seek(s.time));
      if (player.done) {
        this.forget(s.source);
        this.heard = false;
      }
    }
    // The views are told once more only when the last thing that changed has not been told.
    if (!this.heard) this.redraw();
  }

  /** Who owns a free value now, for tests. */
  ownerOf(k: string): object | null {
    return this.owners.get(k)?.source ?? null;
  }

  private release(s: Running): void {
    for (const [k, o] of this.owners) if (o === s) this.owners.delete(k);
  }

  private forget(source: object | Running | null): void {
    if (source === null) return;
    const gone = this.sources.filter((s) => s.source === source || s === source);
    this.sources = this.sources.filter((s) => !gone.includes(s));
    for (const s of gone) this.release(s);
  }
}
