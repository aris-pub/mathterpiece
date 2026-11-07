// Random values, computed from a seed (mtp-bjn0): the same seed, place and position always give
// the same number, so a page shows the same draws on every refresh, and writing a new seed draws
// them all again.

/** A 32-bit hash of whole numbers, each mixed in turn. */
function hash(...xs: number[]): number {
  let h = 0x811c9dc5;
  for (const x of xs) {
    h = Math.imul(h ^ (x >>> 0), 0x01000193);
    h ^= h >>> 15;
    h = Math.imul(h, 0x2c1b3c6d);
    h ^= h >>> 12;
    h = Math.imul(h, 0x297a2d39);
    h ^= h >>> 15;
  }
  return h >>> 0;
}

/** A number from 0 up to 1, not 1, for a seed, the place a random value is written, and k. */
export function unit(seed: number, site: number, k = 0): number {
  return hash(seed, site, k) / 2 ** 32;
}

/** The seed a roll of the dice writes after this one. */
export function nextSeed(seed: number): number {
  return hash(seed, 0x9e3779b9);
}

/** The items of xs in an order the seed and the place pick: Fisher and Yates's shuffle. */
export function shuffle<T>(xs: T[], seed: number, site: number): T[] {
  const out = [...xs];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(unit(seed, site, i) * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}
