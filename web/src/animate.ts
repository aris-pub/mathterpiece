// Runs the animations writers set off, and decides between writers that would write the same
// targets (docs/reference.md, "Concurrency"). Each running source (a button press, a play, a
// click, a held drag) holds the variables and attributes it writes. A newcomer (a source that
// starts, resumes or is moved along, a slider's knob, a toggle's flip, a drag's grab, an
// on-pointermove's write) that would write a target a running source writes is refused when that
// source is exclusive, or was set off by the reader while the newcomer was not; otherwise it
// cancels that source. A refused newcomer does not start at all. An exclusive writer holds the
// lock on its targets for every write, even one that takes no time, and always releases it, even
// when the write throws (the author, 2026-11-11). Time is in seconds; the page moves it forward on
// each animation frame.
import type { Player } from "./player.ts";

/** Who set a writer off, the reader or not (on-view, autoplay), and whether it is exclusive. */
export interface How {
  reader: boolean;
  exclusive: boolean;
  // Whether what it writes is part of the rest state, as an on-view's writes are: such a write
  // puts no play or stepper in explore mode (mtp-wjtd).
  rest?: boolean;
}

interface Running {
  source: object;
  // A drag has no player: it writes as the pointer moves.
  player: Player | null;
  // What it writes, as the shapes' attributes and the variables reached ("id:attr").
  reached: Set<string>;
  time: number;
  paused: boolean;
  // Where it pauses by itself: a stepper plays one step and stops at its end.
  until?: number | undefined;
  how: How;
  // Told when another writer cancels it: a drag then stops following the pointer.
  cancelled?: () => void;
}

// A position is its x and its y, so writing one collides with writing the other.
function ownCovers(target: string): string[] {
  const [id, attr] = target.split(":");
  return attr === "pos" ? [`${id}:x`, `${id}:y`] : [target];
}

export class Scheduler {
  private sources: Running[] = [];
  // Plays and steppers, told of every write of what they move by another writer, whether or
  // not they run: such a write puts one that has not finished into explore mode (mtp-wjtd).
  private watchers: { source: object; reached: Set<string>; written: () => void }[] = [];
  // What moves a view's own state, such as a canvas fading something in: it writes nothing in
  // the model, so it never collides with a writer.
  private tickers: ((seconds: number) => boolean)[] = [];
  // Whether the page has told its views of a change since this last changed what it runs.
  private heard = false;

  /** wake is called whenever something starts moving, so the page can ask for frames; reach
   * gives what a write of a target reaches, so a group's attribute collides with its members'. */
  constructor(
    private redraw: () => void,
    private wake: () => void,
    private reach: (target: string) => string[] = ownCovers,
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
    return this.sources.some((s) => s.how.rest && s.player && !s.paused);
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

  /** Starts a player for a source, from the beginning, and gives false when it is refused. reset,
   * when given, writes first, once the start is not refused. */
  start(player: Player, source: object, how: How, from = 0, reset?: () => void): boolean {
    if (!this.claim(player.targets, source, how)) return false;
    this.forget(source);
    player.release();
    this.run(player, source, how, from, reset);
    return true;
  }

  /** Tells written of every write by another source that reaches one of these targets and is
   * not refused. */
  watch(source: object, targets: string[], written: () => void): void {
    this.watchers = this.watchers.filter((w) => w.source !== source);
    this.watchers.push({ source, reached: this.reached(targets), written });
  }

  unwatch(source: object): void {
    this.watchers = this.watchers.filter((w) => w.source !== source);
  }

  private run(player: Player, source: object, how: How, from: number, reset?: () => void): void {
    this.sources.push({ source, player, reached: this.reached(player.targets), time: from, paused: false, how });
    // A seek that writes something tells the views already, as they stand now.
    this.heard = false;
    if (reset) this.writeOrForget(source, reset);
    this.seekOrForget(player, source, from);
    if (!this.heard) this.redraw();
    this.wake();
  }

  // A player that throws while it writes holds its targets no longer.
  private seekOrForget(player: Player, source: object, time: number): void {
    this.writeOrForget(source, () => player.seek(time));
  }

  private writeOrForget(source: object, write: () => void): void {
    try {
      write();
    } catch (err) {
      this.forget(source);
      throw err;
    }
  }

  /**
   * A write that takes no time, such as a slider's step, an on-pointermove's write or a toggle's
   * flip: a newcomer, refused or not as any is, and given false when refused, so write is not
   * called. An exclusive one holds the lock on its targets while it writes, and releases it after,
   * even when the write throws.
   */
  instant(targets: string[], source: object, how: How, write: () => void): boolean {
    if (!this.claim(targets, source, how)) return false;
    this.locked(this.reached(targets), how, write);
    return true;
  }

  private locked(reached: Set<string>, how: How, write: () => void): void {
    if (!how.exclusive) {
      write();
      return;
    }
    // The lock is a running writer of its own, so the source's own entry, if any, stays as it is.
    const lock = {};
    this.sources.push({ source: lock, player: null, reached, time: 0, paused: false, how });
    try {
      write();
    } finally {
      this.forget(lock);
    }
  }

  /** Holds a player for a source, paused where it stands, writing nothing until it is sought or
   * resumed: a play the reader scrubs keeps the one player, so what it read stays read. */
  hold(player: Player, source: object): void {
    this.forget(source);
    this.sources.push({ source, player, reached: this.reached(player.targets), time: player.time, paused: true, how: { reader: true, exclusive: false } });
  }

  /** A drag held from the grab to the release: a running writer of its targets, which writes as
   * the pointer moves. Gives false when it is refused; cancelled is called if another writer
   * cancels it. */
  grip(targets: string[], source: object, how: How, cancelled: () => void): boolean {
    if (!this.claim(targets, source, how)) return false;
    this.forget(source);
    this.sources.push({ source, player: null, reached: this.reached(targets), time: 0, paused: false, how, cancelled });
    return true;
  }

  /** Ends a source without cancelling it, as a drag's release does. */
  letGo(source: object): void {
    this.forget(source);
  }

  /** Moves a source's player to a time, cancelling every other writer of what it moves; gives
   * false when it is refused. reset, when given, writes first, once the seek is not refused. */
  seek(source: object, time: number, how: How, reset?: () => void): boolean {
    const s = this.sources.find((r) => r.source === source);
    if (!s?.player || !this.claim(s.player.targets, source, how)) return false;
    s.how = how;
    s.time = time;
    this.heard = false;
    // A paused player writes nothing, so it holds no lock; a seek, as from a key, writes at once.
    const player = s.player;
    this.locked(s.reached, how, () => {
      if (reset) this.writeOrForget(source, reset);
      this.seekOrForget(player, source, time);
    });
    if (!this.heard) this.redraw();
    return true;
  }

  /**
   * A newcomer that would write these targets ("id:attr"): gives false, cancelling nothing, when
   * a running source writing one of them refuses it; otherwise cancels every other source writing
   * one of them and gives true. A paused source writes nothing, so it refuses nothing.
   */
  claim(targets: string[], source: object, how: How): boolean {
    const wanted = this.reached(targets);
    const met = this.sources.filter((s) => s.source !== source && [...s.reached].some((t) => wanted.has(t)));
    if (met.some((s) => !s.paused && (s.how.exclusive || (s.how.reader && !how.reader)))) return false;
    for (const s of met) {
      this.forget(s.source);
      s.cancelled?.();
    }
    for (const w of how.rest ? [] : [...this.watchers]) {
      if (w.source !== source && [...w.reached].some((t) => wanted.has(t))) w.written();
    }
    return true;
  }

  pause(source: object): void {
    for (const s of this.sources) if (s.source === source) s.paused = true;
  }

  /** Plays a source's player on from where it stands, to the time until when given; gives false
   * when it is refused. */
  resume(source: object, how: How, until?: number): boolean {
    const s = this.sources.find((r) => r.source === source);
    if (!s?.player || !this.claim(s.player.targets, source, how)) return false;
    s.how = how;
    s.paused = false;
    s.until = until;
    this.wake();
    return true;
  }

  tick(seconds: number): void {
    this.tickers = this.tickers.filter((t) => t(seconds));
    this.heard = false;
    for (const s of [...this.sources]) {
      if (s.paused || !s.player) continue;
      s.time += seconds;
      if (s.until !== undefined && s.time >= s.until) {
        s.time = s.until;
        s.paused = true;
        s.until = undefined;
      }
      this.heard = false;
      this.seekOrForget(s.player, s.source, s.time);
      if (s.player.done) {
        this.forget(s.source);
        this.heard = false;
      }
    }
    // The views are told once more only when the last thing that changed has not been told.
    if (!this.heard) this.redraw();
  }

  private reached(targets: string[]): Set<string> {
    return new Set(targets.flatMap((t) => this.reach(t)));
  }

  private forget(source: object): void {
    this.sources = this.sources.filter((s) => s.source !== source);
  }
}
