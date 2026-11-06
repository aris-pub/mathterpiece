// What only a real browser does for a formula (mtp-bz6h): measuring a term, so its box and
// outline sit around its glyphs, and the page's color reaching glyphs no term colors.
import { describe, expect, it } from "vitest";
import { userEvent } from "vitest/browser";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

function page(body: string): MtpModel {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("formula");
  return model;
}

const term = (name: string) => document.querySelector(`.mtp-term-${name}`) as SVGGElement;

describe("a formula on a page", () => {
  it("draws a term's box around its glyphs, padded in screen pixels", () => {
    page(`<mtp-display model="m" name="d" style="font-size: 20px"></mtp-display>`);
    const rect = term("a").querySelector("rect.mtp-term-box")!;
    const glyphs = term("a").querySelector("use, path")!.getBoundingClientRect();
    const box = rect.getBoundingClientRect();
    expect(box.width).toBeGreaterThan(glyphs.width);
    // A padding of 2 pixels on each side.
    expect(box.width - glyphs.width).toBeGreaterThan(3);
    expect(box.width - glyphs.width).toBeLessThan(5);
    expect(box.left).toBeLessThan(glyphs.left);
  });

  it("takes the page's color where no term colors it", () => {
    page(`<mtp-display model="m" name="d" style="color: rgb(0, 0, 255)"></mtp-display>`);
    expect(getComputedStyle(term("v")).color).toBe("rgb(0, 0, 255)");
    expect(getComputedStyle(term("a")).color).toBe("rgb(0, 128, 128)");
  });

  it("plays on-enter when the pointer comes onto a term", async () => {
    const model = page(`<mtp-display model="m" name="d" style="font-size: 40px"></mtp-display>`);
    const rt = model.runtime!;
    await userEvent.hover(term("a"));
    await new Promise((r) => setTimeout(r, 100));
    expect(rt.value(rt.id("f.a"), "background")).not.toBeNull();
  });
});

describe("the pointer on a term", () => {
  it("is on it between its glyphs, where its box is unpainted", async () => {
    const model = page(`<mtp-display model="m" name="d" style="font-size: 40px"></mtp-display>`);
    const rt = model.runtime!;
    const box = term("a").querySelector("rect.mtp-term-box")!.getBoundingClientRect();
    const hit = document.elementFromPoint(box.left + 1, box.top + 1);
    expect(hit?.closest(".mtp-term-a")).not.toBeNull();
    expect(rt.value(rt.id("f.a"), "background")).toBeNull();
  });
});
