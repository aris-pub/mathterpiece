import { describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { draw } from "../src/svg.ts";

const ID = [1, 0, 0, 0, 1, 0];
const style = { transform: ID, x: 0, y: 0, fill: "#000000ff", stroke: "none", "stroke-width": 1, opacity: 1, "fill-opacity": 1, "stroke-opacity": 1 };
const read = (part: string) => ["read", 2, part];

// label (2) is a font token; t (3) uses it; plain (4) has no font.
function world(label: Record<string, unknown>, textAttrs: Record<string, unknown> = {}) {
  const objects: Omit<Obj, "id">[] = [
    { kind: "canvas", name: "view", attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 10, transform: ID }, shows: [1] },
    { kind: "root", name: "s", attrs: { transform: ID }, members: [3, 4] },
    { kind: "font", name: "label", attrs: { family: "", style: "normal", weight: 400, size: 1, ...label } },
    {
      kind: "text",
      name: "t",
      parent: 1,
      attrs: { ...style, value: "x", "font-family": read("family"), "font-style": read("style"), "font-weight": read("weight"), "font-size": read("size"), ...textAttrs },
    },
    { kind: "text", name: "plain", parent: 1, attrs: { ...style, value: "y", "font-family": "", "font-style": "normal", "font-weight": 400, "font-size": 1 } },
  ];
  const doc: Doc = { mtp: 1, objects: objects.map((o, id) => ({ ...o, id }) as Obj), functions: {}, names: {}, depends: {} };
  return draw(new Runtime(doc), 0);
}

const texts = (svg: SVGSVGElement) => [...svg.querySelectorAll("text")] as SVGElement[];

describe("type tokens on a canvas", () => {
  it("draw family, style and weight as CSS variables the page can set", () => {
    const [t] = texts(world({ family: "Georgia, serif", style: "italic", weight: 600, size: 0.6 }));
    expect(t!.style.getPropertyValue("font-family")).toBe("var(--mtp-label-family, Georgia, serif)");
    expect(t!.style.getPropertyValue("font-style")).toBe("var(--mtp-label-style, italic)");
    expect(t!.style.getPropertyValue("font-weight")).toBe("var(--mtp-label-weight, 600)");
    expect(t!.getAttribute("font-size")).toBe("0.6");
  });

  it("leave the family to the page when the token has none", () => {
    const [t] = texts(world({}));
    expect(t!.style.getPropertyValue("font-family")).toBe("var(--mtp-label-family)");
  });

  it("let a text set a part itself", () => {
    const [t] = texts(world({ style: "italic" }, { "font-style": "normal" }));
    expect(t!.style.getPropertyValue("font-style")).toBe("normal");
  });

  it("leave a text without a font to the page", () => {
    const [, plain] = texts(world({}));
    expect(plain!.style.getPropertyValue("font-family")).toBe("");
  });
});
