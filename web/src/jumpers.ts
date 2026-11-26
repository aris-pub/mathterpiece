// The arithmetic of the jumpers (docs/spec/controls.md): where the thumb of a slider, a range
// slider or a dial stops, which thumb of a range slider a press on its track moves, what an arrow
// key moves it by, where its ticks are, how a typed number is read, and what list a multi-select
// writes. The elements that draw them are in elements.ts.
import { equal, roundHalfAway, wrapInto } from "./builtins.ts";

/**
 * The numbers that a thumb runs over: from lo to hi along a slider's track (lo may be the larger),
 * or once around a dial's ring, from lo up to hi, which wraps. step is null for none.
 */
export interface Scale {
  lo: number;
  hi: number;
  step: number | null;
  int: boolean;
  wrap: boolean;
}

// More decimals than this are float noise, not what an author wrote.
const MAX_DECIMALS = 12;

/** How many decimals a number is written with, up to MAX_DECIMALS. */
function decimals(x: number): number {
  if (!Number.isFinite(x) || Number.isInteger(x)) return 0;
  const text = String(Math.abs(x));
  if (text.includes("e")) return MAX_DECIMALS;
  return Math.min(text.length - text.indexOf(".") - 1, MAX_DECIMALS);
}

/**
 * x without the noise that adding binary fractions leaves: rounded to the decimals of the numbers
 * it was made from, so 0.1 + 0.2 gives 0.3. With none given, to MAX_DECIMALS.
 */
export function tidy(x: number, ...from: number[]): number {
  const d = from.length ? Math.max(...from.map(decimals)) : MAX_DECIMALS;
  const v = Number(x.toFixed(d));
  return v === 0 ? 0 : v;
}

const stepOf = (s: Scale): number | null => (s.step !== null && s.step > 0 && Number.isFinite(s.step) ? s.step : null);

/** The allowed value of a scale nearest to v. */
export function snap(s: Scale, v: number): number {
  const step = stepOf(s);
  if (s.wrap) {
    const w = wrapInto(v, s.lo, s.hi);
    if (step !== null) return tidy(wrapInto(s.lo + Math.round((w - s.lo) / step) * step, s.lo, s.hi), s.lo, step);
    return s.int ? wrapInto(roundHalfAway(w), s.lo, s.hi) : w;
  }
  const [min, max] = s.lo <= s.hi ? [s.lo, s.hi] : [s.hi, s.lo];
  if (step !== null) {
    const dir = s.hi >= s.lo ? 1 : -1;
    const last = Math.floor((max - min) / step + 1e-9);
    const k = Math.min(Math.max(Math.round(((v - s.lo) * dir) / step), 0), last);
    return tidy(s.lo + k * step * dir, s.lo, step);
  }
  if (s.int) return Math.min(Math.max(roundHalfAway(v), Math.ceil(min)), Math.floor(max));
  return Math.min(Math.max(v, min), max);
}

/** How far along a scale a value stands, from 0 at lo to 1 at hi. */
export function fractionOf(s: Scale, v: number): number {
  if (s.hi === s.lo || !Number.isFinite(v)) return 0;
  if (s.wrap) return (wrapInto(v, s.lo, s.hi) - s.lo) / (s.hi - s.lo);
  return Math.min(Math.max((v - s.lo) / (s.hi - s.lo), 0), 1);
}

/** The allowed value nearest to the point that lies a fraction f along a scale. */
export function valueAt(s: Scale, f: number): number {
  return snap(s, s.lo + f * (s.hi - s.lo));
}

/** What an arrow key moves a thumb by: a step, else 1 on an int, else 1/100 of the range. */
export function keyAmount(s: Scale): number {
  return stepOf(s) ?? (s.int ? 1 : Math.abs(s.hi - s.lo) / 100);
}

/** The value n arrow presses from v, toward hi for n > 0. A slider stops at its ends, and a dial
 * comes round. */
export function stepFrom(s: Scale, v: number, n: number): number {
  const dir = s.hi >= s.lo ? 1 : -1;
  const amount = keyAmount(s);
  return snap(s, tidy(v + n * amount * dir, v, amount));
}

/** The thumb of a range slider that a press at the value v moves: the low one (0) when v is at
 * or below the middle of the two thumbs' values, else the high one (1). This is the nearer thumb,
 * and the low one when the press is midway. When both thumbs sit on one spot, it is the thumb on
 * the side of the press, since the other one could not move there. */
export function pressedThumb(low: number, high: number, v: number): 0 | 1 {
  return v > (low + high) / 2 ? 1 : 0;
}

// More ticks than this could not be told apart, and would only slow the page down.
const MAX_TICKS = 1000;

/** The values of the ticks: every ticks, else every step, from lo, and none with neither. On a dial
 * the tick at hi is the one at lo. */
export function tickValues(s: Scale, ticks: number | null): number[] {
  const every = ticks !== null && ticks > 0 && Number.isFinite(ticks) ? ticks : stepOf(s);
  if (every === null) return [];
  const span = Math.abs(s.hi - s.lo);
  const dir = s.hi >= s.lo ? 1 : -1;
  const out: number[] = [];
  for (let k = 0; k < MAX_TICKS; k++) {
    const at = k * every;
    if (s.wrap ? at >= span - every * 1e-9 : at > span + every * 1e-9) break;
    out.push(tidy(s.lo + at * dir, s.lo, every));
  }
  return out;
}

/** A typed number, or null when the text is not one. Both the hyphen and the minus sign are
 * read as minus. */
export function parseNumber(text: string): number | null {
  const t = text.trim().replace(/−/g, "-");
  if (t === "") return null;
  const v = Number(t);
  return Number.isFinite(v) ? v : null;
}

/** For each option, whether its value is in the list. */
export function chosenIn(list: unknown[], options: unknown[]): boolean[] {
  return options.map((o) => list.some((v) => equal(v, o)));
}

/** The list after the reader chooses option i: with it added, or removed when it was there. The
 * chosen options come in the order of the options, then the values that are no option, which another
 * writer may have put there, in their own order (the author, 2026-11-26). */
export function toggledList(list: unknown[], options: unknown[], i: number): unknown[] {
  const chosen = chosenIn(list, options);
  chosen[i] = !chosen[i];
  const others = list.filter((v) => !options.some((o) => equal(v, o)));
  return [...options.filter((_, j) => chosen[j]), ...others];
}
