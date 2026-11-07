// Colors for light and dark pages (mtp-m34w.1; docs/reference.md, "Colors"). A light-dark color
// is painted as CSS's light-dark(), so the page's color-scheme picks the mode; a color computed
// from one while drawing is worked out for each mode on its own.
import { describe, expect, it } from "vitest";
import { Player } from "../src/player.ts";
import { paintCss } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a light-dark color", () => {
  it("is painted as the CSS that picks one by the page's color-scheme", () => {
    const rt = load("light-dark");
    expect(paintCss(rt, rt.id("plain"), "fill")).toBe("light-dark(#999999ff, #5a5f6bff)");
  });

  it("is a token's value, inside its CSS variable", () => {
    const rt = load("light-dark");
    expect(paintCss(rt, rt.id("tok"), "fill")).toBe("var(--mtp-ink, light-dark(#1f2a44ff, #e8e4d8ff))");
  });

  it("is mixed by CSS when a token is mixed", () => {
    const rt = load("light-dark");
    expect(paintCss(rt, rt.id("mixed"), "fill")).toBe(
      "color-mix(in srgb, var(--mtp-ink, light-dark(#1f2a44ff, #e8e4d8ff)) 50%, var(--mtp-paper, #ffffffff) 50%)",
    );
  });

  it("is mixed for each mode while drawing", () => {
    const rt = load("light-dark");
    expect(rt.value(rt.id("live"), null)).toBe("light-dark(#800000ff, #ff8080ff)");
    rt.write(rt.id("t"), null, 1);
    // Red in both modes is one color.
    expect(rt.value(rt.id("live"), null)).toBe("#ff0000ff");
  });

  it("built while drawing picks each mode's own value", () => {
    const rt = load("light-dark");
    expect(rt.value(rt.id("picked"), "fill")).toBe("light-dark(#ff0000ff, #e8e4d8ff)");
    expect(paintCss(rt, rt.id("picked"), "fill")).toBe(
      "light-dark(#ff0000ff, var(--mtp-ink, light-dark(#1f2a44ff, #e8e4d8ff)))",
    );
  });

  it("reads its light value's channels", () => {
    const rt = load("light-dark");
    expect(rt.value(rt.id("channel"), null)).toBe(0);
  });

  it("equals another when both modes do", () => {
    const rt = load("light-dark");
    expect(rt.value(rt.id("matches"), null)).toBe(true);
  });

  it("reads as its CSS in text", () => {
    const rt = load("light-dark");
    expect(rt.value(rt.id("label"), "value")).toBe("light-dark(#808080ff, #c0c0c0ff)");
  });

  it("moves for each mode", () => {
    const rt = load("light-dark");
    const p = new Player(rt, rt.id("fade"));
    p.seek(0.5);
    expect(rt.value(rt.id("moved"), "fill")).toBe("light-dark(#808080ff, #000000ff)");
    p.seek(1);
    expect(rt.value(rt.id("moved"), "fill")).toBe("light-dark(#ffffffff, #000000ff)");
  });
});
