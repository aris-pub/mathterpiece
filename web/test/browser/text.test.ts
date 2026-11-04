// A text shows its string as written, though SVG collapses white space by default
// (docs/reference.md, "Shapes"). Only a real browser lays text out, so widths are checked here.
import { beforeEach, describe, expect, it } from "vitest";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

function width(name: string): number {
  const rt = (document.querySelector("mtp-model") as MtpModel).runtime!;
  return (document.querySelector(`[data-mtp-id="${rt.id(name)}"]`) as SVGTextElement).getBBox().width;
}

describe("a text's white space", () => {
  beforeEach(() => {
    document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m" name="v" style="display: block; width: 400px"></mtp-canvas>`;
    (document.querySelector("mtp-model") as MtpModel).doc = doc("spaces");
  });

  it("keeps leading spaces", () => {
    expect(width("lead")).toBeGreaterThan(width("one"));
  });

  it("keeps spaces in a row", () => {
    expect(width("double")).toBeGreaterThan(width("single"));
  });

  it("shows a tab or a newline as one space", () => {
    expect(width("tab")).toBeCloseTo(width("single"));
    expect(width("newline")).toBeCloseTo(width("single"));
  });
});
