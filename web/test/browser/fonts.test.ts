import { afterEach, describe, expect, it } from "vitest";
import type { Doc, Obj } from "../../src/doc.ts";
import { define, frames, type MtpModel } from "../../src/elements.ts";

define();
frames.request = () => {};

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, x: 1, y: 1, fill: "#000000ff", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };
const read = (part: string) => ["read", 2, part];
const objects: Omit<Obj, "id">[] = [
  { kind: "canvas", name: "view", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [1] },
  { kind: "root", name: "s", attrs: { transform: ID }, members: [3] },
  { kind: "font", name: "label", attrs: { family: "Georgia, serif", style: "italic", weight: 600, size: 1 } },
  {
    kind: "text",
    name: "t",
    parent: 1,
    attrs: { ...style, value: "x", "font-family": read("family"), "font-style": read("style"), "font-weight": read("weight"), "font-size": read("size") },
  },
  { kind: "readout", name: "r", attrs: { value: "1.155", "font-family": read("family"), "font-style": read("style"), "font-weight": read("weight") } },
  { kind: "readout", name: "plain", attrs: { value: "2", "font-family": "", "font-style": "normal", "font-weight": 400 } },
];
const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: { label: 2, t: 3, r: 4, plain: 5 }, depends: {} };

async function page(css = "") {
  document.head.querySelector("#page-css")?.remove();
  const sheet = document.createElement("style");
  sheet.id = "page-css";
  sheet.textContent = css;
  document.head.append(sheet);
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><mtp-canvas model="m"></mtp-canvas>
    <p style="font-family: monospace; font-weight: 300">d = <mtp-readout model="m" name="r"></mtp-readout>, n = <mtp-readout model="m" name="plain"></mtp-readout></p>`;
  (document.querySelector("mtp-model") as MtpModel).doc = doc;
  await new Promise((r) => setTimeout(r, 0));
  const text = getComputedStyle(document.querySelector("mtp-canvas text")!);
  const [r, plain] = [...document.querySelectorAll("mtp-readout")].map((e) => getComputedStyle(e));
  return { text, r: r!, plain: plain! };
}

afterEach(() => document.body.replaceChildren());

describe("type tokens in a real page", () => {
  it("use the figure's defaults when the page says nothing", async () => {
    const { text, r } = await page();
    expect([text.fontFamily, text.fontStyle, text.fontWeight]).toEqual(["Georgia, serif", "italic", "600"]);
    expect([r.fontFamily, r.fontStyle, r.fontWeight]).toEqual(["Georgia, serif", "italic", "600"]);
  });

  it("follow the page's CSS, each part separately", async () => {
    const { text, r } = await page(":root { --mtp-label-family: Arial; --mtp-label-weight: 700; }");
    expect([text.fontFamily, text.fontStyle, text.fontWeight]).toEqual(["Arial", "italic", "700"]);
    expect(r.fontFamily).toBe("Arial");
  });

  it("let the page's own rules on a readout win", async () => {
    const { r } = await page("mtp-readout { font-style: normal; }");
    expect(r.fontStyle).toBe("normal");
  });

  it("leave a readout without a font as its paragraph", async () => {
    const { plain } = await page();
    expect([plain.fontFamily, plain.fontStyle, plain.fontWeight]).toEqual(["monospace", "normal", "300"]);
  });
});
