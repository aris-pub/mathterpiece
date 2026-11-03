// Colors computed from tokens reach the browser as CSS, so the page's CSS restyles them too
// (docs/mtpc.md, "Objects": variable).
import { describe, expect, it } from "vitest";
import type { Runtime } from "../src/runtime.ts";
import { load } from "./helpers.ts";
import { paintCss } from "../src/svg.ts";

function setup(): [Runtime, (name: string) => string] {
  const rt = load("tokens");
  return [rt, (name) => paintCss(rt, rt.id(name), "fill")];
}

const ink = "var(--mtp-ink, #000080ff)";
const paper = "var(--mtp-paper, #ffffffff)";

describe("a color computed from tokens", () => {
  it("mixes the tokens' CSS variables", () => {
    const [, fill] = setup();
    expect(fill("mixed")).toBe(`color-mix(in srgb, ${ink} 75%, ${paper} 25%)`);
  });

  it("lightens and darkens a token by the amount it has while drawing", () => {
    const [rt, fill] = setup();
    expect(fill("lighter")).toBe(`color-mix(in srgb, ${ink} 75%, #ffffffff 25%)`);
    rt.write(rt.id("t"), null, 0.5);
    expect(fill("lighter")).toBe(`color-mix(in srgb, ${ink} 50%, #ffffffff 50%)`);
    expect(fill("darker")).toBe(`color-mix(in srgb, ${ink} 50%, #000000ff 50%)`);
  });

  it("follows if and cond to the token chosen", () => {
    const [rt, fill] = setup();
    expect(fill("chosen")).toBe(ink);
    rt.write(rt.id("on"), null, false);
    expect(fill("chosen")).toBe(paper);
    expect(fill("picked")).toBe(ink);
    rt.write(rt.id("pick"), null, 1);
    expect(fill("picked")).toBe("#ff0000ff");
    rt.write(rt.id("pick"), null, 2);
    expect(fill("picked")).toBe(paper);
  });

  it("follows a motif parameter given a token", () => {
    const [rt] = setup();
    const tagged = rt.id("tagged");
    const dot = rt.objects.findIndex((o, i) => o.kind === "circle" && rt.parent(i) === tagged);
    expect(paintCss(rt, dot, "fill")).toBe(ink);
  });

  it("stays a plain color when it reads no token", () => {
    const [, fill] = setup();
    expect(fill("plain")).toBe("#ff0000ff");
  });

});
