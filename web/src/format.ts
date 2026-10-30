// Shows values the way Python does: str() of a float, and the format mini-language of
// f-strings. mtp strings follow Python in every backend, so this must match it exactly,
// including rounding half to even on the exact binary value of a float.

export type Kind = "int" | "ratio" | "real" | "complex" | "str" | "bool" | string;

/** Python's str() of a float: the shortest digits that read back the same. */
export function pyStr(x: number): string {
  if (Number.isNaN(x)) return "nan";
  if (x === Infinity) return "inf";
  if (x === -Infinity) return "-inf";
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const sign = x < 0 ? "-" : "";
  const [mantissa, expText] = Math.abs(x).toExponential().split("e");
  const digits = (mantissa ?? "").replace(".", "");
  const exp = Number(expText);
  if (exp < -4 || exp >= 16) {
    const rest = digits.slice(1);
    const head = rest ? `${digits[0]}.${rest}` : `${digits[0]}`;
    return `${sign}${head}e${exp < 0 ? "-" : "+"}${String(Math.abs(exp)).padStart(2, "0")}`;
  }
  return sign + placePoint(digits, exp + 1, true);
}

// Digits with the decimal point after `point` of them (point may be negative or past the end).
function placePoint(digits: string, point: number, keepZero: boolean): string {
  let whole: string;
  let frac: string;
  if (point <= 0) {
    whole = "0";
    frac = "0".repeat(-point) + digits;
  } else if (point >= digits.length) {
    whole = digits + "0".repeat(point - digits.length);
    frac = "";
  } else {
    whole = digits.slice(0, point);
    frac = digits.slice(point);
  }
  frac = frac.replace(/0+$/, "");
  if (!frac) return keepZero ? `${whole}.0` : whole;
  return `${whole}.${frac}`;
}

// The exact decimal value of a finite double, as all its digits and where the point goes.
function exactDigits(x: number): { digits: string; point: number } {
  if (x === 0) return { digits: "0", point: 1 };
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, Math.abs(x));
  const bits = view.getBigUint64(0);
  const biased = Number((bits >> 52n) & 0x7ffn);
  let mantissa = bits & ((1n << 52n) - 1n);
  let exp: number;
  if (biased === 0) {
    exp = -1074;
  } else {
    mantissa |= 1n << 52n;
    exp = biased - 1075;
  }
  if (exp >= 0) return { digits: (mantissa << BigInt(exp)).toString(), point: 0 };
  const digits = (mantissa * 5n ** BigInt(-exp)).toString();
  return { digits, point: -exp };
}

// Rounds a digit string to `keep` digits, half to even, using the digits that follow.
function roundDigits(digits: string, keep: number): { digits: string; carry: boolean } {
  if (keep >= digits.length) return { digits: digits.padEnd(keep, "0"), carry: false };
  if (keep < 0) return { digits: "", carry: false };
  const head = digits.slice(0, keep);
  const tail = digits.slice(keep);
  const first = tail.charCodeAt(0) - 48;
  const rest = tail.slice(1).replace(/0/g, "");
  const last = keep > 0 ? head.charCodeAt(keep - 1) - 48 : 0;
  const up = first > 5 || (first === 5 && (rest !== "" || last % 2 === 1));
  if (!up) return { digits: head, carry: false };
  // A round-up that adds a digit (9.995 to 10.00) comes back one digit longer, with carry set.
  const raised = (BigInt(head || "0") + 1n).toString();
  if (raised.length > keep) return { digits: raised, carry: true };
  return { digits: raised.padStart(keep, "0"), carry: false };
}

// |x| in fixed notation with `places` digits after the point.
function fixed(x: number, places: number): string {
  const { digits, point } = exactDigits(Math.abs(x));
  const whole = Math.max(digits.length - point, 0);
  const padded = whole === 0 ? "0".repeat(point - digits.length) + digits : digits;
  const wholeDigits = Math.max(padded.length - point, 0);
  const all = wholeDigits === 0 ? `0${padded}` : padded;
  const intLen = Math.max(wholeDigits, 1);
  const { digits: result, carry } = roundDigits(all, intLen + places);
  const len = carry ? intLen + 1 : intLen;
  const intPart = result.slice(0, len).replace(/^0+(?=\d)/, "") || "0";
  const fracPart = result.slice(len);
  return places > 0 ? `${intPart}.${fracPart}` : intPart;
}

// |x| in scientific notation with `places` digits after the point.
function scientific(x: number, places: number, upper: boolean): string {
  const abs = Math.abs(x);
  let mantissa: string;
  let exp: number;
  if (abs === 0) {
    mantissa = "0".repeat(places + 1);
    exp = 0;
  } else {
    const { digits, point } = exactDigits(abs);
    const lead = digits.replace(/^0+/, "");
    exp = digits.length - point - (digits.length - lead.length) - 1;
    const { digits: kept, carry } = roundDigits(lead, places + 1);
    mantissa = kept.slice(0, places + 1);
    if (carry) exp += 1;
  }
  const head = places > 0 ? `${mantissa[0]}.${mantissa.slice(1)}` : `${mantissa[0]}`;
  const e = upper ? "E" : "e";
  return `${head}${e}${exp < 0 ? "-" : "+"}${String(Math.abs(exp)).padStart(2, "0")}`;
}

// Python's 'g': fixed or scientific depending on the exponent, trailing zeros removed (kept,
// with the point, under '#'). With no type and a precision (atLeastOne), Python switches to
// scientific one exponent sooner and keeps one digit after the point in fixed notation.
function general(
  x: number,
  precision: number,
  upper: boolean,
  alternate: boolean,
  atLeastOne: boolean,
): string {
  const p = precision === 0 ? 1 : precision;
  const abs = Math.abs(x);
  const sci = scientific(abs, p - 1, upper);
  const exp = abs === 0 ? 0 : Number(sci.slice(sci.search(/[eE]/) + 1));
  const limit = atLeastOne ? p - 1 : p;
  let out: string;
  if (exp >= -4 && exp < limit) {
    out = fixed(abs, p - 1 - exp);
    if (!alternate && out.includes(".")) out = out.replace(/0+$/, "").replace(/\.$/, "");
    if (alternate && !out.includes(".")) out += ".";
    if (atLeastOne && !out.includes(".")) out += ".0";
    else if (atLeastOne && out.endsWith(".")) out += "0";
  } else {
    const [m, rest] = sci.split(/[eE]/);
    let mant = m ?? "";
    if (!alternate && mant.includes(".")) mant = mant.replace(/0+$/, "").replace(/\.$/, "");
    if (alternate && !mant.includes(".")) mant += ".";
    out = `${mant}${upper ? "E" : "e"}${rest}`;
  }
  return out;
}

const SPEC =
  /^(?:(?<fill>[\s\S])?(?<align>[<>=^]))?(?<sign>[-+ ])?(?<z>z)?(?<alt>#)?(?<zero>0)?(?<width>\d+)?(?<group>[,_])?(?:\.(?<precision>\d+))?(?<type>[bcdeEfFgGnosxX%])?$/;

function groupDigits(digits: string, sep: string, size: number): string {
  let out = "";
  for (let i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % size === 0) out += sep;
    out += digits[i];
  }
  return out;
}

/** Python's format(value, spec), for a value of the given mtp type. */
export function format(value: unknown, spec: string, kind: Kind): string {
  const m = SPEC.exec(spec);
  if (!m?.groups) throw new Error(`invalid format spec ${JSON.stringify(spec)}`);
  const g = m.groups;
  const type = g.type ?? "";
  const width = g.width ? Number(g.width) : 0;
  const precision = g.precision !== undefined ? Number(g.precision) : undefined;
  let fill = g.fill ?? " ";
  let align = g.align ?? "";
  if (g.zero && !g.align) {
    fill = "0";
    align = "=";
  }

  if (kind === "str" || typeof value === "string") {
    if (type && type !== "s") throw new Error(`format spec ${JSON.stringify(spec)} is not for text`);
    if (g.sign || align === "=" || g.alt || g.group) {
      throw new Error(`format spec ${JSON.stringify(spec)} is not for text`);
    }
    let text = String(value);
    if (precision !== undefined) text = text.slice(0, precision);
    return pad(text, "", width, fill, align || "<");
  }

  if (typeof value !== "number") throw new Error(`cannot format ${String(value)}`);
  const isInt = kind === "int";
  if (!isInt && "bcdoxXn".includes(type) && type !== "") {
    throw new Error(`format spec ${JSON.stringify(spec)} needs an int`);
  }
  if (isInt && precision !== undefined && (type === "" || "bcdoxXn".includes(type))) {
    throw new Error("an int cannot take a precision");
  }
  const negative = value < 0 || Object.is(value, -0);
  const abs = Math.abs(value);
  let body: string;
  let prefix = "";

  if (isInt && (type === "" || "bcdoxXn".includes(type))) {
    const n = BigInt(Math.round(abs));
    const base = { b: 2, o: 8, x: 16, X: 16 }[type as "b"] ?? 10;
    body = n.toString(base);
    if (type === "X") body = body.toUpperCase();
    if (type === "c") body = String.fromCodePoint(Number(n));
    if (g.alt && base !== 10) prefix = { 2: "0b", 8: "0o", 16: type === "X" ? "0X" : "0x" }[base] ?? "";
    if (g.group) body = groupDigits(body, g.group, base === 10 ? 3 : 4);
  } else {
    const t = type || (precision !== undefined ? "" : "repr");
    if (t === "repr") {
      body = isInt ? String(Math.round(abs)) : pyStr(abs);
    } else if (t === "f" || t === "F") {
      body = Number.isFinite(abs) ? fixed(abs, precision ?? 6) : specialFloat(abs, t === "F");
      if (g.alt && !body.includes(".")) body += ".";
    } else if (t === "e" || t === "E") {
      body = Number.isFinite(abs) ? scientific(abs, precision ?? 6, t === "E") : specialFloat(abs, t === "E");
    } else if (t === "%") {
      body = `${fixed(abs * 100, precision ?? 6)}%`;
    } else if (t === "g" || t === "G") {
      body = general(abs, precision ?? 6, t === "G", Boolean(g.alt), false);
    } else {
      body = general(abs, precision ?? 6, false, Boolean(g.alt), !isInt);
    }
    if (g.group) {
      const [whole = "", ...rest] = body.split(".");
      if (/^\d+$/.test(whole)) body = [groupDigits(whole, g.group, 3), ...rest].join(".");
    }
  }
  // z: a number that rounds to zero is shown without its minus sign.
  const zero = Boolean(g.z) && !/[1-9]/.test(body.replace(/[eE][+-]?\d+$/, ""));
  const sign = negative && !zero ? "-" : g.sign === "+" ? "+" : g.sign === " " ? " " : "";
  return pad(body, sign + prefix, width, fill, align || ">");
}

function specialFloat(abs: number, upper: boolean): string {
  const text = Number.isNaN(abs) ? "nan" : "inf";
  return upper ? text.toUpperCase() : text;
}

function pad(body: string, sign: string, width: number, fill: string, align: string): string {
  const length = sign.length + [...body].length;
  const room = Math.max(width - length, 0);
  if (align === "=") return sign + fill.repeat(room) + body;
  if (align === "<") return sign + body + fill.repeat(room);
  if (align === "^") {
    const left = Math.floor(room / 2);
    return fill.repeat(left) + sign + body + fill.repeat(room - left);
  }
  return fill.repeat(room) + sign + body;
}
