// Namespaces (mtp-4rc; docs/reference.md, "Namespaces").
import { describe, expect, it } from "vitest";
import { draw, paintCss } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a namespace", () => {
  it("is read through its members", () => {
    const rt = load("namespace");
    expect(rt.value(rt.id("c"), "r")).toBe(0.4);
    rt.write(rt.id("theme.gap"), null, 1.5);
    expect(rt.value(rt.id("c"), "r")).toBe(1.5);
  });

  it("keeps its colors as tokens, named by the namespace", () => {
    const rt = load("namespace");
    expect(paintCss(rt, rt.id("c"), "fill")).toBe("var(--mtp-theme-ink, #1f2a44ff)");
    // A color member that is bound is a token of its own, as a bound color variable is.
    expect(paintCss(rt, rt.id("d"), "fill")).toBe("var(--mtp-theme-soft, #8b8e96ff)");
    expect(paintCss(rt, rt.id("e"), "fill")).toBe("var(--mtp-theme-accents-warm, #e76f51ff)");
  });

  it("is never drawn", () => {
    const rt = load("namespace");
    const svg = draw(rt, rt.id("v"));
    expect(svg.querySelector(`[data-mtp-id="${rt.id("theme")}"]`)).toBeNull();
  });
});
