// A namespace read through a variable typed with an interface (mtp-ateh, mtp-4rc).
import { describe, expect, it } from "vitest";
import { paintCss } from "../src/svg.ts";
import { load } from "./helpers.ts";

describe("a namespace held by a variable typed with an interface", () => {
  it("is read through, and follows when the variable holds another", () => {
    const rt = load("interface");
    expect(rt.value(rt.id("c"), "r")).toBe(0.4);
    expect(rt.value(rt.id("c"), "fill")).toBe("#1f2a44ff");
    rt.write(rt.id("dark"), null, true);
    expect(rt.value(rt.id("c"), "r")).toBe(1);
    expect(rt.value(rt.id("c"), "fill")).toBe("#e8e4d8ff");
  });

  it("keeps a color read through it a token", () => {
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
