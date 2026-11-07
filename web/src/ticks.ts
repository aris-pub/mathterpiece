// A slider's ticks: round values across the range its knob covers, each placed where the knob
// gives that value.

/** Round values from lo to hi, about five of them, in steps of 1, 2 or 5 times a power of ten. */
export function niceTicks(a: number, b: number): number[] {
  const [lo, hi] = a <= b ? [a, b] : [b, a];
  const span = hi - lo;
  if (!(span > 0) || !Number.isFinite(span)) return [];
  const rough = span / 4;
  const mag = 10 ** Math.floor(Math.log10(rough));
  const err = rough / mag;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
  // Rounding to the step's own decimals keeps 0.1 + 0.2 from showing as 0.30000000000000004.
  const decimals = Math.max(0, -Math.floor(Math.log10(step)));
  const out: number[] = [];
  for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + step * 1e-9; k++) {
    const v = Number((k * step).toFixed(decimals));
    out.push(v === 0 ? 0 : v);
  }
  return out;
}

export interface Tick {
  value: number;
  /** Where the knob stands for the value, from 0 to 1. */
  u: number;
}

/** The ticks of a knob whose position u gives at(u), found by halving, since an eased or
 *  backwards range does not place its values evenly. A range that is not of numbers has none. */
export function placeTicks(at: (u: number) => unknown): Tick[] {
  const a = at(0);
  const b = at(1);
  if (typeof a !== "number" || typeof b !== "number") return [];
  const up = b >= a;
  return niceTicks(a, b).map((value) => {
    let lo = 0;
    let hi = 1;
    for (let n = 0; n < 50; n++) {
      const mid = (lo + hi) / 2;
      const v = at(mid) as number;
      if (v < value === up) lo = mid;
      else hi = mid;
    }
    return { value, u: (lo + hi) / 2 };
  });
}
