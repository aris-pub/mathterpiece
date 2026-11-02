import { describe, expect, it } from "vitest";
import { format, pyStr } from "../src/format.ts";

describe("pyStr, Python's str() of a float", () => {
  it.each([
    [2, "2.0"],
    [0.5, "0.5"],
    [-3, "-3.0"],
    [137.50776405003785, "137.50776405003785"],
    [0.1 + 0.2, "0.30000000000000004"],
    [1e-5, "1e-05"],
    [0.0001, "0.0001"],
    [1.5e-7, "1.5e-07"],
    [1e16, "1e+16"],
    [123456789012345.0, "123456789012345.0"],
    [1234567890123456.0, "1234567890123456.0"],
    [1.2345e20, "1.2345e+20"],
    [0, "0.0"],
    [-0, "-0.0"],
    [Infinity, "inf"],
    [-Infinity, "-inf"],
    [NaN, "nan"],
  ])("%s", (x, text) => {
    expect(pyStr(x)).toBe(text);
  });
});

describe("format, Python's format mini-language", () => {
  it.each([
    [3.14159, ".2f", "real", "3.14"],
    [2.5, ".0f", "real", "3"],
    [3.5, ".0f", "real", "4"],
    [7, "03d", "int", "007"],
    [7, ">4", "int", "   7"],
    [7, "<4", "int", "7   "],
    [7, "^5", "int", "  7  "],
    [7, "*^5", "int", "**7**"],
    [-7, "05d", "int", "-0007"],
    [42, "+d", "int", "+42"],
    [42, " d", "int", " 42"],
    [1234567, ",d", "int", "1,234,567"],
    [1234567.891, ",.2f", "real", "1,234,567.89"],
    [1234567, "_d", "int", "1_234_567"],
    [0.25, ".0%", "real", "25%"],
    [0.12345, ".1%", "real", "12.3%"],
    [1234.5, ".3e", "real", "1.235e+03"],
    [1234.5, "E", "real", "1.234500E+03"],
    [0.000123, ".2e", "real", "1.23e-04"],
    [1234.5, "g", "real", "1234.5"],
    [1.23e-05, "g", "real", "1.23e-05"],
    [123456789, ".3g", "int", "1.23e+08"],
    [255, "x", "int", "ff"],
    [255, "#x", "int", "0xff"],
    [255, "X", "int", "FF"],
    [5, "b", "int", "101"],
    [8, "o", "int", "10"],
    [2.0, "", "real", "2.0"],
    [1.5, "8.3f", "real", "   1.500"],
    [-1.5, "=8.2f", "real", "-   1.50"],
    [2.0, ".3", "real", "2.0"],
    [1e+20, "f", "real", "100000000000000000000.000000"],
    [0.5, "+.1f", "real", "+0.5"],
    [2, "", "int", "2"],
    [0.3333333333333333, ".5", "real", "0.33333"],
    [12345.678, "10.1f", "real", "   12345.7"],
    [-0.0, ".1f", "real", "-0.0"],
  ])("%s with %j as %s", (x, spec, kind, text) => {
    expect(format(x, spec, kind)).toBe(text);
  });

  it.each([
    [-0.0001, "+z.3f", "+0.000"],
    [-0.0001, "z.1%", "0.0%"],
    [-0.4, "z.0f", "0"],
    [-1.2, "z.1f", "-1.2"],
    [-0.0, "z.2f", "0.00"],
    [-1e-05, "z.2e", "-1.00e-05"],
    [0.0001, "+z.3f", "+0.000"],
  ])("%s with %j turns negative zero into zero, as z does in Python", (x, spec, text) => {
    expect(format(x, spec, "real")).toBe(text);
  });

  it("formats strings", () => {
    expect(format("ab", "*^6", "str")).toBe("**ab**");
    expect(format("ab", ">4", "str")).toBe("  ab");
  });

  it("rejects specs that do not fit the type", () => {
    expect(() => format("ab", ".2f", "str")).toThrow();
    expect(() => format(1.5, "d", "real")).toThrow();
  });
});

// Values and specs with the text the compiler gives them (test/format_cases.py writes the file).
import cases from "./data/format-cases.json";

describe("format agrees with the compiler on a large sample", () => {
  it("matches every case", () => {
    const wrong: string[] = [];
    for (const [x, spec, kind, text] of cases as [number, string, string, string][]) {
      const got = spec === "repr" ? pyStr(x) : format(x, spec, kind);
      if (got !== text) wrong.push(`${x} ${JSON.stringify(spec)} ${kind}: ${got} != ${text}`);
    }
    expect(wrong.slice(0, 20)).toEqual([]);
  });
});
