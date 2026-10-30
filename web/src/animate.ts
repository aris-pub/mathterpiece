// Moves values toward states over time, for buttons, steps and play. A port of the Python
// backend's animator. Time is in seconds; the page moves it forward on each animation frame.
import { isPaint, mixCss } from "./colors.ts";
import type { Runtime } from "./runtime.ts";

export { parseColor } from "./colors.ts";

export const EASES: Record<string, (t: number) => number> = {
  linear: (t) => t,
  "ease-in": (t) => t * t * t,
  "ease-out": (t) => 1 - (1 - t) ** 3,
  "ease-in-out": (t) => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2),
};

// One value moving toward a state, from where it was to the target worked out when the move
// started.
interface Track {
  obj: number;
  attr: string;
  begin: unknown;
  target: unknown;
  start: number;
  duration: number;
  ease: string;
}

type Step = ["wait", number] | ["to", number, number, string];

export class Animator {
  private now = 0;
  private tracks: Track[] = [];
  private tour: { steps: Step[] } | null = null;
  private step = 0;
  private stepStart = 0;
  private morphStart = 0;
  private morphEnd = 0;

  /** wake is called whenever something starts moving, so the page can ask for frames. */
  constructor(
    private rt: Runtime,
    private redraw: () => void,
    private wake: () => void,
  ) {}

  busy(): boolean {
    return this.tracks.length > 0 || this.tour !== null || this.rt.morphs.size > 0;
  }

  cancel(): void {
    this.tracks = [];
    this.tour = null;
    this.rt.morphs.clear();
  }

  go(state: number, duration: number, ease: string, start: number = this.now): void {
    for (const [i, attr, target] of this.rt.targets(state)) {
      const begin = this.rt.value(i, attr);
      if (duration > 0 && this.rt.kind(i) === "text" && attr === "value" && begin !== target) {
        this.rt.morphs.set(i, [String(begin), 0]);
        this.morphStart = start;
        this.morphEnd = start + duration;
      }
      if (duration > 0 && blendable(begin, target)) {
        this.tracks.push({ obj: i, attr, begin, target, start, duration, ease });
      } else {
        this.rt.write(i, attr, target);
      }
    }
    this.redraw();
    this.wake();
  }

  play(id: number): void {
    this.cancel();
    const control = this.rt.obj(id);
    if (control.start !== null && control.start !== undefined) {
      for (const [i, attr, target] of this.rt.targets(control.start)) this.rt.write(i, attr, target);
    }
    this.tour = { steps: (control.steps ?? []) as Step[] };
    this.step = 0;
    this.stepStart = this.now;
    if (this.tour.steps.length === 0) this.tour = null;
    else this.beginStep();
    this.redraw();
    this.wake();
  }

  private beginStep(): void {
    const step = this.tour?.steps[this.step];
    if (step?.[0] === "to") this.go(step[1], step[2], step[3], this.stepStart);
  }

  tick(seconds: number): void {
    this.now += seconds;
    while (this.tour) {
      const step = this.tour.steps[this.step] as Step;
      const end = this.stepStart + (step[0] === "wait" ? step[1] : step[2]);
      if (this.now < end) break;
      this.update(end);
      this.step += 1;
      this.stepStart = end;
      if (this.step === this.tour.steps.length) this.tour = null;
      else this.beginStep();
    }
    this.update(this.now);
    this.redraw();
  }

  // Writes every moving value for the given moment, and drops the ones that have arrived.
  private update(now: number): void {
    for (const track of [...this.tracks]) {
      const t = track.duration === 0 ? 1 : Math.min(1, (now - track.start) / track.duration);
      const ease = EASES[track.ease] ?? EASES.linear!;
      this.rt.write(track.obj, track.attr, t >= 1 ? track.target : blend(track.begin, track.target, ease(t)));
      if (t >= 1) this.tracks.splice(this.tracks.indexOf(track), 1);
    }
    if (this.rt.morphs.size > 0) {
      const t = Math.min(1, (now - this.morphStart) / Math.max(this.morphEnd - this.morphStart, 1e-12));
      for (const [k, [old]] of this.rt.morphs) this.rt.morphs.set(k, [old, t]);
      if (t >= 1) this.rt.morphs.clear();
    }
  }
}

function blendable(a: unknown, b: unknown): boolean {
  if (typeof a === "boolean" || typeof b === "boolean") return false;
  if (typeof a === "number" && typeof b === "number") return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length;
  if (a === b) return false;
  return isPaint(a) && isPaint(b);
}

/**
 * Partway from a to b. Numbers and points move in JavaScript; colors are mixed by CSS, in sRGB,
 * with 'none' as transparent, so color tokens blend with whatever the page made of them.
 */
export function blend(a: unknown, b: unknown, t: number): unknown {
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, i) => x + ((b[i] as number) - x) * t);
  if (isPaint(a) && isPaint(b)) return mixCss(a, b, t);
  return (a as number) + ((b as number) - (a as number)) * t;
}
