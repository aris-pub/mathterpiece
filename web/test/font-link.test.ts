// A font's part read from another font falls back to that font's CSS variable (the author,
// 2026-11-05), so a page restyling the family restyles the role too.
import { describe, expect, it } from "vitest";
import { draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a font part read from another font", () => {
  it("falls back to the other font's CSS variable", () => {
    const rt = load("font-link");
    const text = draw(rt, rt.id("v")).querySelector(`[data-mtp-id="${rt.id("t")}"]`) as SVGElement;
    expect(text.style.getPropertyValue("font-family")).toBe(
      "var(--mtp-variable-family, var(--mtp-serif-family, Georgia, serif))",
    );
    expect(text.style.getPropertyValue("font-style")).toBe("var(--mtp-variable-style, italic)");
  });
});
