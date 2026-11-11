// Runs the animations writers set off, and decides between writers that would write the same
// targets (docs/reference.md, "Concurrency"). Each running source (a button press, a play, a
// click, a held drag) holds the variables and attributes it writes. A newcomer (a source that
// starts, resumes or is moved along, a slider's knob, a toggle's flip, a drag's grab, an
// on-pointermove's write) that would write a target a running source writes is refused when that
// source is exclusive, or was set off by the reader while the newcomer was not; otherwise it
// cancels that source. A refused newcomer does not start at all. Time is in seconds; the page
// moves it forward on each animation frame.
import type { Player } from "./player.ts";

/** Who set a writer off, the reader or not (on-view, autoplay), and whether it is exclusive. */
export interface How {
  reader: boolean;
  exclusive: boolean;
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

  /** Starts a player for a source, from the beginning; gives false when it is refused. */
  start(player: Player, source: object, how: How, from = 0): boolean {
    if (!this.claim(player.targets, source, how)) return false;
    this.forget(source);
    player.release();
    this.run(player, source, how, from);
    return true;
  }

  /** Plays on a player another writer cancelled, from where it stood: the moves it cut off start
   * again from the values as they are now. Gives false when it is refused. */
  again(player: Player, source: object, how: How): boolean {
    if (!this.claim(player.targets, source, how)) return false;
    this.forget(source);
    player.cut();
    this.run(player, source, how, player.time);
    return true;
  }

  private run(player: Player, source: object, how: How, from: number): void {
    this.sources.push({ source, player, reached: this.reached(player.targets), time: from, paused: false, how });
    // A seek that writes something tells the views already, as they stand now.
    this.heard = false;
    player.seek(from);
    if (!this.heard) this.redraw();
    this.wake();
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
   * false when it is refused. */
  seek(source: object, time: number, how: How): boolean {
    const s = this.sources.find((r) => r.source === source);
    if (!s?.player || !this.claim(s.player.targets, source, how)) return false;
    s.how = how;
    s.time = time;
    this.heard = false;
    s.player.seek(time);
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
      s.player.seek(s.time);
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
