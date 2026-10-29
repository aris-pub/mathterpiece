import { describe, expect, it } from "vitest";
import { FORMAT_VERSION, supports } from "../src/index.ts";

describe("supports", () => {
  it("reads the current format", () => {
    expect(supports({ mtp: FORMAT_VERSION })).toBe(true);
  });

  it("refuses other versions", () => {
    expect(supports({ mtp: 2 })).toBe(false);
    expect(supports({})).toBe(false);
  });

  it("has a page to draw on", () => {
    expect(document.createElementNS("http://www.w3.org/2000/svg", "svg").tagName).toBe("svg");
  });
});
