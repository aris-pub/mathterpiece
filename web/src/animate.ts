// Runs the animations writers set off, and decides every write a writer makes, as
// docs/concurrency-model.md says (the author, 2026-11-13). Each free value written, a target,
// has at most one owner: the running writer whose write it last accepted. A write is accepted
// when its writer's priority is higher than the owner's, or the same and its writer was triggered
// later. Then the writer becomes the owner, and the writer that owned the value before is
// cancelled on every value. A rejected write cancels nothing, and its writer writes that value no
// more for the rest of its effect. Each value is decided on its own. Time is in seconds; the page
// moves it forward on each frame.
import type { Player } from "./player.ts";

// The priorities writers have when they give none: the page's (on-view, on-rest), the reader's,
// and a gesture's (on-drag, a held slider's knob, on-pointermove).
export const PAGE = 300;
export const READER = 500;
export const GESTURE = 700;

/** Who set a writer off, the reader or not (on-view), whether it is a gesture the reader is
 * making now (a dragged shape, a slider's knob held, a pointer moving), and its own (priority n),
 * if it gives one. */
export interface How {
  reader: boolean;
  priority?: number | undefined;
  held?: boolean;
  // Whether what it writes is part of the rest state, as an on-view's writes are: such a write
  // puts no play or stepper in explore mode (mtp-wjtd).
  rest?: boolean;
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
  // How many times as fast as written it plays: an on-view hurried to its end runs faster.
  speed?: number;
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
  // Plays and steppers, told of every accepted write of what they move by another writer, whether
  // or not they run: such a write puts one that has not finished into explore mode (mtp-wjtd).
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
    return this.tickers.length > 0 || this.sources.some((s) => s.player && !s.paused);
  }

  /** Whether a writer of the rest state, an on-view, still runs. */
  resting(): boolean {
    // One that loops forever never ends, so it is not waited for.
    return this.sources.some((s) => s.how.rest && s.player && !s.paused && Number.isFinite(s.player.duration));
  }

  /** Speeds up every writer of the rest state still running so each ends within seconds. */
  hurry(seconds: number): void {
    for (const s of this.sources) {
      if (!s.how.rest || !s.player || s.paused || !Number.isFinite(s.player.duration)) continue;
      const left = s.player.duration - s.time;
      if (left > seconds) s.speed = left / seconds;
    }
  }

  /** Moves view state with the clock; tick gives whether it has more to do. */
  addTicker(tick: (seconds: number) => boolean): void {
    this.tickers.push(tick);
    this.wake();
  }

  running(source: object): boolean {
    return this.sources.some((s) => s.source === source && !s.paused);
  }

  playerOf(source: object): Player | null {
    return this.sources.find((s) => s.source === source)?.player ?? null;
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
    if (!by.how.rest) {
      const reaches = (r: string) => k === r || k.startsWith(`${r}.`);
      for (const w of [...this.watchers]) if (w.source !== by.source && [...w.reached].some(reaches)) w.written();
    }
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

  /** Starts a player for a source, from the beginning. reset, when given, writes first. Every
   * start is made: a write it makes may be rejected, but the writer is not. */
  start(player: Player, source: object, how: How, from = 0, reset?: () => void): boolean {
    this.forget(source);
    player.release();
    this.run(player, source, how, from, reset);
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

  private run(player: Player, source: object, how: How, from: number, reset?: () => void): void {
    const s = this.entry(source, player, how, from);
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

  /** Holds a player for a source, paused where it stands, writing nothing until it is sought or
   * resumed: a play the reader scrubs keeps the one player, so what it read stays read. */
  hold(player: Player, source: object): void {
    this.forget(source);
    this.sources.push({ ...this.entry(source, player, { reader: true }, player.time), paused: true });
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

  /** Moves a source's player to a time, its writes decided as any are. reset, when given, writes
   * first. */
  seek(source: object, time: number, how: How, reset?: () => void): boolean {
    const s = this.sources.find((r) => r.source === source);
    if (!s?.player) return false;
    s.how = how;
    // A jump or a resume is a trigger of its own, so a new effect.
    s.born = ++this.triggers;
    s.blocked.clear();
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

  /** A paused source writes nothing, so it owns nothing. */
  pause(source: object): void {
    for (const s of this.sources) {
      if (s.source !== source) continue;
      s.paused = true;
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
      if (s.paused || !s.player || !this.sources.includes(s)) continue;
      s.time += seconds * (s.speed ?? 1);
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
