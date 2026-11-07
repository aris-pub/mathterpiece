// A light-dark color follows the color-scheme of where it is drawn (mtp-m34w.1), as CSS's
// light-dark() does, so only a real browser can tell.
import { describe, expect, it } from "vitest";
import { type MtpModel, define } from "../../src/elements.ts";
import { doc } from "../helpers.ts";

define();

function fills(scheme: string, style = ""): Record<string, string> {
  document.body.innerHTML =
    `<mtp-model id="m"></mtp-model>` +
    `<div style="color-scheme: ${scheme}; ${style}"><mtp-canvas model="m" name="v"></mtp-canvas></div>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc("light-dark");
  const rt = model.runtime!;
  const fill = (name: string) => getComputedStyle(document.querySelector(`[data-mtp-id="${rt.id(name)}"]`)!).fill;
  return { plain: fill("plain"), tok: fill("tok"), picked: fill("picked") };
}

describe("a light-dark color", () => {
  it("is its light value where the color-scheme is light", () => {
    expect(fills("light")).toEqual({ plain: "rgb(153, 153, 153)", tok: "rgb(31, 42, 68)", picked: "rgb(255, 0, 0)" });
  });

  it("is its dark value where the color-scheme is dark", () => {
    expect(fills("dark")).toEqual({ plain: "rgb(90, 95, 107)", tok: "rgb(232, 228, 216)", picked: "rgb(232, 228, 216)" });
  });

  it("gives way to a page's own value for a token", () => {
    expect(fills("dark", "--mtp-ink: rgb(1, 2, 3)").tok).toBe("rgb(1, 2, 3)");
  });
});
