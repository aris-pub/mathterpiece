// Moves values toward states over time, for buttons, steps and play. A port of the Python
// backend's animator. Time is in seconds; the page moves it forward on each animation frame.
import { Runtime } from "./runtime.ts";

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
  if (typeof a !== "string" || typeof b !== "string" || a === b) return false;
  return (a === "none" || parseColor(a) !== null) && (b === "none" || parseColor(b) !== null);
}

/** Partway from a to b. Colors blend in RGB, and 'none' counts as the other color, transparent. */
export function blend(a: unknown, b: unknown, t: number): unknown {
  if (Array.isArray(a) && Array.isArray(b)) return a.map((x, i) => x + ((b[i] as number) - x) * t);
  if (typeof a === "string" && typeof b === "string") {
    const ca = a === "none" ? transparent(b) : parseColor(a);
    const cb = b === "none" ? transparent(a) : parseColor(b);
    if (!ca || !cb) return t < 1 ? a : b;
    return hex(ca.map((x, i) => x + ((cb[i] as number) - x) * t) as Rgba);
  }
  return (a as number) + ((b as number) - (a as number)) * t;
}

type Rgba = [number, number, number, number];

function transparent(color: string): Rgba | null {
  const c = parseColor(color);
  return c ? [c[0], c[1], c[2], 0] : null;
}

function hex([r, g, b, a]: Rgba): string {
  const two = (x: number) => Math.round(x).toString(16).padStart(2, "0");
  return `#${two(r)}${two(g)}${two(b)}${a >= 1 ? "" : two(a * 255)}`;
}

/** Reads hex colors and CSS color names, as red, green, blue (0 to 255) and alpha (0 to 1). */
export function parseColor(text: string): Rgba | null {
  let s = text.trim().toLowerCase();
  if (!s.startsWith("#")) {
    const named = NAMED[s];
    if (!named) return null;
    s = `#${named}`;
  }
  let digits = s.slice(1);
  if (!/^[0-9a-f]+$/.test(digits)) return null;
  if (digits.length === 3 || digits.length === 4) digits = [...digits].map((d) => d + d).join("");
  if (digits.length !== 6 && digits.length !== 8) return null;
  const n = (k: number) => parseInt(digits.slice(k, k + 2), 16);
  return [n(0), n(2), n(4), digits.length === 8 ? n(6) / 255 : 1];
}

// The CSS named colors.
const NAMED: Record<string, string> = Object.fromEntries(
  (
  "aliceblue:f0f8ff,antiquewhite:faebd7,aqua:00ffff,aquamarine:7fffd4,azure:f0ffff,beige:f5f5dc,bis" +
  "que:ffe4c4,black:000000,blanchedalmond:ffebcd,blue:0000ff,blueviolet:8a2be2,brown:a52a2a,burlywo" +
  "od:deb887,cadetblue:5f9ea0,chartreuse:7fff00,chocolate:d2691e,coral:ff7f50,cornflowerblue:6495ed" +
  ",cornsilk:fff8dc,crimson:dc143c,cyan:00ffff,darkblue:00008b,darkcyan:008b8b,darkgoldenrod:b8860b" +
  ",darkgray:a9a9a9,darkgreen:006400,darkgrey:a9a9a9,darkkhaki:bdb76b,darkmagenta:8b008b,darkoliveg" +
  "reen:556b2f,darkorange:ff8c00,darkorchid:9932cc,darkred:8b0000,darksalmon:e9967a,darkseagreen:8f" +
  "bc8f,darkslateblue:483d8b,darkslategray:2f4f4f,darkslategrey:2f4f4f,darkturquoise:00ced1,darkvio" +
  "let:9400d3,deeppink:ff1493,deepskyblue:00bfff,dimgray:696969,dimgrey:696969,dodgerblue:1e90ff,fi" +
  "rebrick:b22222,floralwhite:fffaf0,forestgreen:228b22,fuchsia:ff00ff,gainsboro:dcdcdc,ghostwhite:" +
  "f8f8ff,gold:ffd700,goldenrod:daa520,gray:808080,green:008000,greenyellow:adff2f,grey:808080,hone" +
  "ydew:f0fff0,hotpink:ff69b4,indianred:cd5c5c,indigo:4b0082,ivory:fffff0,khaki:f0e68c,lavender:e6e" +
  "6fa,lavenderblush:fff0f5,lawngreen:7cfc00,lemonchiffon:fffacd,lightblue:add8e6,lightcoral:f08080" +
  ",lightcyan:e0ffff,lightgoldenrodyellow:fafad2,lightgray:d3d3d3,lightgreen:90ee90,lightgrey:d3d3d" +
  "3,lightpink:ffb6c1,lightsalmon:ffa07a,lightseagreen:20b2aa,lightskyblue:87cefa,lightslategray:77" +
  "8899,lightslategrey:778899,lightsteelblue:b0c4de,lightyellow:ffffe0,lime:00ff00,limegreen:32cd32" +
  ",linen:faf0e6,magenta:ff00ff,maroon:800000,mediumaquamarine:66cdaa,mediumblue:0000cd,mediumorchi" +
  "d:ba55d3,mediumpurple:9370db,mediumseagreen:3cb371,mediumslateblue:7b68ee,mediumspringgreen:00fa" +
  "9a,mediumturquoise:48d1cc,mediumvioletred:c71585,midnightblue:191970,mintcream:f5fffa,mistyrose:" +
  "ffe4e1,moccasin:ffe4b5,navajowhite:ffdead,navy:000080,oldlace:fdf5e6,olive:808000,olivedrab:6b8e" +
  "23,orange:ffa500,orangered:ff4500,orchid:da70d6,palegoldenrod:eee8aa,palegreen:98fb98,paleturquo" +
  "ise:afeeee,palevioletred:db7093,papayawhip:ffefd5,peachpuff:ffdab9,peru:cd853f,pink:ffc0cb,plum:" +
  "dda0dd,powderblue:b0e0e6,purple:800080,rebeccapurple:663399,red:ff0000,rosybrown:bc8f8f,royalblu" +
  "e:4169e1,saddlebrown:8b4513,salmon:fa8072,sandybrown:f4a460,seagreen:2e8b57,seashell:fff5ee,sien" +
  "na:a0522d,silver:c0c0c0,skyblue:87ceeb,slateblue:6a5acd,slategray:708090,slategrey:708090,snow:f" +
  "ffafa,springgreen:00ff7f,steelblue:4682b4,tan:d2b48c,teal:008080,thistle:d8bfd8,tomato:ff6347,tu" +
  "rquoise:40e0d0,violet:ee82ee,wheat:f5deb3,white:ffffff,whitesmoke:f5f5f5,yellow:ffff00,yellowgre" +
  "en:9acd32"
  )
    .split(",")
    .map((pair) => pair.split(":") as [string, string]),
);
