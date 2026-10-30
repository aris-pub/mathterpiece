// Runs the animations controls set off. Each running source (a button press, a play) owns the
// targets its animation writes. When a new source starts, or a slider, drag or toggle claims
// targets, any running source that writes one of them is cancelled as a whole: the reader's newest
// action wins. Sources that share no target run together. Time is in seconds; the page moves it
// forward on each animation frame.
import type { Player } from "./player.ts";
import type { Runtime } from "./runtime.ts";

interface Running {
  source: object;
  player: Player;
  time: number;
  paused: boolean;
}

export class Scheduler {
  private sources: Running[] = [];
  // Things that move only a view's own state, such as a canvas fading something in: they write
  // nothing in the scene, so they never collide with anything.
  private tickers: ((seconds: number) => boolean)[] = [];

  /** wake is called whenever something starts moving, so the page can ask for frames. */
  constructor(
    private rt: Runtime,
    private redraw: () => void,
    private wake: () => void,
  ) {}

  /** Whether anything is running. */
  busy(): boolean {
    return this.tickers.length > 0 || this.sources.some((s) => !s.paused);
  }

  /** Moves view state with the clock; tick returns whether it still has more to do. */
  addTicker(tick: (seconds: number) => boolean): void {
    this.tickers.push(tick);
    this.wake();
  }

  /** Whether a source is running, rather than paused, done or cancelled. */
  running(source: object): boolean {
    return this.sources.some((s) => s.source === source && !s.paused);
  }

  /** The player a source is running or has paused, if any. */
  playerOf(source: object): Player | null {
    return this.sources.find((s) => s.source === source)?.player ?? null;
  }

  /** Starts a player for a source, from the beginning. */
  start(player: Player, source: object): void {
    this.forget(source);
    this.claim(player.targets, source);
    this.sources.push({ source, player, time: 0, paused: false });
    player.seek(0);
    this.redraw();
    this.wake();
  }

  /** Cancels every other source that writes any of these targets ("id.attr"). */
  claim(targets: string[], source: object): void {
    const wanted = new Set(targets.flatMap(covers));
    for (const s of [...this.sources]) {
      if (s.source !== source && s.player.targets.flatMap(covers).some((t) => wanted.has(t))) this.cancel(s);
    }
  }

  pause(source: object): void {
    for (const s of this.sources) if (s.source === source) s.paused = true;
  }

  resume(source: object): void {
    const s = this.sources.find((r) => r.source === source);
    if (!s) return;
    this.claim(s.player.targets, source);
    s.paused = false;
    this.wake();
  }

  /** Moves a running source to where its player has jumped. */
  jumped(source: object, time: number): void {
    const s = this.sources.find((r) => r.source === source);
    if (s) s.time = time;
    this.redraw();
    this.wake();
  }

  tick(seconds: number): void {
    this.tickers = this.tickers.filter((t) => t(seconds));
    for (const s of [...this.sources]) {
      if (s.paused) continue;
      s.time += seconds;
      s.player.seek(s.time);
      if (s.player.done) this.forget(s.source);
    }
    this.redraw();
  }

  private cancel(s: Running): void {
    for (const t of s.player.targets) this.rt.morphs.delete(Number(t.split(".")[0]));
    this.forget(s.source);
  }

  private forget(source: object): void {
    this.sources = this.sources.filter((s) => s.source !== source);
  }
}

// A position is its x and its y, so writing one collides with writing the other.
function covers(target: string): string[] {
  const [id, attr] = target.split(".");
  return attr === "pos" ? [`${id}.x`, `${id}.y`] : [target];
}
