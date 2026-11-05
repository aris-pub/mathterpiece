// Colormaps (mtp-nua; docs/reference.md, "Colormaps"): a call is compiled in place, so the colors
// it mixes stay the tokens they read.
import { describe, expect, it } from "vitest";
import { paintCss } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a colormap", () => {
  it("mixes its tokens' CSS variables", () => {
    const rt = load("colormap");
    expect(paintCss(rt, rt.id("c"), "fill")).toBe(
      "color-mix(in srgb, var(--mtp-navy, #000080ff) 75%, var(--mtp-paper, #ffffffff) 25%)",
    );
  });

  it("follows the value it is given", () => {
    const rt = load("colormap");
    expect(rt.value(rt.id("d"), "fill")).toBe("#000001ff");
    rt.write(rt.id("t"), null, 0.75);
    expect(rt.value(rt.id("d"), "fill")).toBe("#000002ff");
    expect(paintCss(rt, rt.id("c"), "fill")).toBe(
      "color-mix(in srgb, var(--mtp-navy, #000080ff) 25%, var(--mtp-paper, #ffffffff) 75%)",
    );
  });
});
