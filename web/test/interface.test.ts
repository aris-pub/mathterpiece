// A namespace read through a parameter typed with an interface (mtp-ateh, mtp-4rc). A variable
// is never declared with an interface (the author, 2026-11-16).
import { describe, expect, it } from "vitest";
import { paintCss } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a namespace given to a function through an interface", () => {
  it("is read through, and follows when the argument is another", () => {
    const rt = load("interface");
    expect(rt.value(rt.id("c"), "r")).toBe(0.4);
    expect(rt.value(rt.id("c"), "fill")).toBe("#1f2a44ff");
    rt.write(rt.id("dark"), null, true);
    expect(rt.value(rt.id("c"), "r")).toBe(1);
    expect(rt.value(rt.id("c"), "fill")).toBe("#e8e4d8ff");
  });

  // mtp-dliq: a color returned by a function is no longer a token.
  it.fails("keeps a color read through it a token", () => {
    const rt = load("interface");
    expect(paintCss(rt, rt.id("c"), "fill")).toBe("var(--mtp-day-ink, #1f2a44ff)");
    rt.write(rt.id("dark"), null, true);
    expect(paintCss(rt, rt.id("c"), "fill")).toBe("var(--mtp-night-ink, #e8e4d8ff)");
  });
});

describe("a motif's parameter declared with an interface (mtp-4rc, step 3)", () => {
  it("is read through, and follows when it holds another", () => {
    const rt = load("interface");
    expect(rt.value(rt.id("fixed.face"), "fill")).toBe("#f6f1e7ff");
    expect(rt.value(rt.id("follows.face"), "fill")).toBe("#f6f1e7ff");
    rt.write(rt.id("dark"), null, true);
    expect(rt.value(rt.id("fixed.face"), "fill")).toBe("#f6f1e7ff");
    expect(rt.value(rt.id("follows.face"), "fill")).toBe("#14161cff");
  });

  it("keeps a color read through it a token", () => {
    const rt = load("interface");
    expect(paintCss(rt, rt.id("fixed.face"), "fill")).toBe("var(--mtp-day-paper, #f6f1e7ff)");
    rt.write(rt.id("dark"), null, true);
    expect(paintCss(rt, rt.id("follows.face"), "fill")).toBe("var(--mtp-night-paper, #14161cff)");
  });
});
