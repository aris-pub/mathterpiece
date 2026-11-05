/**
 * A token's CSS custom property. An imported token is kept as file.name, and a CSS name takes no
 * dot, so house.ink is --mtp-house-ink (the author, 2026-11-04).
 */
export function cssVariable(name: string): string {
  return `--mtp-${name.replace(/\./g, "-")}`;
}
