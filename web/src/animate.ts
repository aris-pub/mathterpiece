// Runs the animations writers set off. Each running source (a button press, a play, a click)
// owns the variables and attributes its animation writes. When a source starts, or a slider, drag or toggle
// writes, any running source that writes one of the same ones is cancelled: the newest writer
// wins, whatever its kind (docs/reference.md, "Controls"). Time is in seconds; the page moves it
// forward on each animation frame.
import type { Player } from "./player.ts";

interface Running {
  source: object;
  player: Player;
  time: number;
  paused: boolean;
  // Where it pauses by itself: a stepper plays one step and stops at its end.
  until?: number | undefined;
}

export class Scheduler {
  private sources: Running[] = [];
  // What moves a view's own state, such as a canvas fading something in: it writes nothing in
  // the model, so it never collides with a writer.
  private tickers: ((seconds: number) => boolean)[] = [];
  // Whether the page has told its views of a change since this last changed what it runs.
  private heard = false;

  /** wake is called whenever something starts moving, so the page can ask for frames. */
  constructor(
    private redraw: () => void,
    private wake: () => void,
  ) {}

  /** The page calls this whenever it tells its views of a change. */
  told(): void {
    this.heard = true;
  }

  busy(): boolean {
    return this.tickers.length > 0 || this.sources.some((s) => !s.paused);
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

  /** Starts a player for a source, from the beginning. */
  start(player: Player, source: object, from = 0): void {
    this.forget(source);
    this.claim(player.targets, source);
    player.release();
    this.sources.push({ source, player, time: from, paused: false });
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
    this.sources.push({ source, player, time: player.time, paused: true });
  }

  /** Moves a source's player to a time, cancelling every other writer of what it moves. */
  seek(source: object, time: number): void {
    const s = this.sources.find((r) => r.source === source);
    if (!s) return;
    this.claim(s.player.targets, source);
    s.time = time;
    this.heard = false;
    s.player.seek(time);
    if (!this.heard) this.redraw();
  }

  /** Cancels every other source that writes any of these ("id:attr"). */
  claim(targets: string[], source: object): void {
    const wanted = new Set(targets.flatMap(covers));
    for (const s of [...this.sources]) {
      if (s.source !== source && s.player.targets.flatMap(covers).some((t) => wanted.has(t))) {
        this.forget(s.source);
      }
    }
  }

  pause(source: object): void {
    for (const s of this.sources) if (s.source === source) s.paused = true;
  }

  /** Plays a source's player on from where it stands, to the time until when given. */
  resume(source: object, until?: number): void {
    const s = this.sources.find((r) => r.source === source);
    if (!s) return;
    this.claim(s.player.targets, source);
    s.paused = false;
    s.until = until;
    this.wake();
  }

  tick(seconds: number): void {
    this.tickers = this.tickers.filter((t) => t(seconds));
    this.heard = false;
    for (const s of [...this.sources]) {
      if (s.paused) continue;
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

  private forget(source: object): void {
    this.sources = this.sources.filter((s) => s.source !== source);
  }
}

// A position is its x and its y, so writing one collides with writing the other.
function covers(target: string): string[] {
  const [id, attr] = target.split(":");
  return attr === "pos" ? [`${id}:x`, `${id}:y`] : [target];
}
