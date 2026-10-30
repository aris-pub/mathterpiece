// Colors. For now every color is RGBA: written as #rrggbbaa, mixed in sRGB. Mixing is done by
// CSS (color-mix), never here, so color tokens mix with whatever the page made of them.

/** A color token: drawn as a CSS variable the page may set, with the figure's default. */
export class Token {
  constructor(
    readonly name: string,
    readonly fallback: string,
  ) {}

  get css(): string {
    return `var(--mtp-${this.name}, ${this.fallback})`;
  }
}

/** Whether a value can be drawn as a color: a token, 'none', a known color or a CSS color function. */
export function isPaint(value: unknown): boolean {
  if (value instanceof Token) return true;
  if (typeof value !== "string") return false;
  return value === "none" || isCssColorFunction(value) || parseColor(value) !== null;
}

function isCssColorFunction(value: string): boolean {
  return /^(color-mix|var)\(/.test(value.trim());
}

/** A value as CSS for fill or stroke. A string that names no color is a drawing error. */
export function cssColor(value: unknown): string {
  if (value instanceof Token) return value.css;
  if (value === "none") return "transparent";
  if (typeof value === "string" && isPaint(value)) return value;
  throw new Error(`${JSON.stringify(value)} is not a color`);
}

/** t of the way from a to b, left to CSS: color-mix in sRGB. */
export function mixCss(a: unknown, b: unknown, t: number): string {
  if (!(t >= 0 && t <= 1)) throw new Error("the amount must be between 0 and 1");
  const percent = Math.round(t * 1e6) / 1e4;
  return `color-mix(in srgb, ${cssColor(a)}, ${cssColor(b)} ${percent}%)`;
}

/** Whether a string is a color only CSS can work out, such as a mix. */
export function needsCss(value: unknown): value is string {
  return typeof value === "string" && isCssColorFunction(value);
}

/** A color the browser computed, such as "rgb(232, 228, 216)" or "color(srgb 1 0 0 / 0.5)". */
export function parseComputed(text: string): Rgba | null {
  const nums = (s: string) => s.split(/[\s,/]+/).filter(Boolean).map(Number);
  let m = /^rgba?\((.*)\)$/.exec(text.trim());
  if (m?.[1]) {
    const [r = 0, g = 0, b = 0, a = 1] = nums(m[1]);
    return [r, g, b, a];
  }
  m = /^color\(srgb (.*)\)$/.exec(text.trim());
  if (m?.[1]) {
    const [r = 0, g = 0, b = 0, a = 1] = nums(m[1]);
    return [r * 255, g * 255, b * 255, a];
  }
  return parseColor(text);
}

/** Equality, where two strings that both name colors are equal if the colors are. */
export function sameColor(a: string, b: string): boolean {
  if (a === b) return true;
  const ca = parseColor(a);
  const cb = parseColor(b);
  return ca !== null && cb !== null && hex(ca) === hex(cb);
}

export type Rgba = [number, number, number, number];

/** A color as #rrggbbaa, the one form colors take in the JSON for now. */
export function hex([r, g, b, a]: Rgba): string {
  const two = (x: number) => Math.round(x).toString(16).padStart(2, "0");
  return `#${two(r)}${two(g)}${two(b)}${two(a * 255)}`;
}

/** Reads hex colors and CSS color names, as red, green, blue (0 to 255) and alpha (0 to 1). */
export function parseColor(text: string): Rgba | null {
  let s = text.trim().toLowerCase();
  if (s === "transparent") return [0, 0, 0, 0];
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
