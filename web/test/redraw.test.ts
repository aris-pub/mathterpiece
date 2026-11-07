// Drawing a canvas again into the SVG it drew before, keeping what has not changed: what it
// shows must be what a first drawing shows.
import { describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { DrawMemo, draw } from "../src/svg.ts";
import { load } from "./helpers.ts";

// What an element shows, whatever the order its attributes and style were set in. Marker and
// clip ids name the SVG they are drawn in, so that part is left out.
function markup(el: Element): string {
  const attrs = [...el.attributes]
    .filter((a) => a.name !== "style")
    .map((a) => `${a.name}=${a.value}`)
    .sort();
  const style = (el as SVGElement).style;
  const styles = [...Array(style.length).keys()].map((k) => `${style.item(k)}:${style.getPropertyValue(style.item(k))}`).sort();
  const inner = el.children.length ? [...el.children].map(markup).join("") : (el.textContent ?? "");
  return `<${el.tagName} ${[...attrs, ...styles].join(" ")}>${inner}</${el.tagName}>`.replace(/mtp-(head|clip)-\d+-/g, "mtp-$1-");
}

function redrawn(rt: Runtime, canvas: number) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
  const memo = new DrawMemo();
  draw(rt, canvas, svg, undefined, undefined, memo);
  return {
    svg,
    // Draws again, and checks it shows what a first drawing would.
    again: () => {
      draw(rt, canvas, svg, undefined, undefined, memo);
      expect(markup(svg)).toBe(markup(draw(rt, canvas)));
    },
  };
}

describe("drawing again", () => {
  it("follows every write as a first drawing does", () => {
    const rt = load("draw");
    const { again } = redrawn(rt, rt.id("v"));
    again();
    rt.write(rt.id("k"), null, 2);
    again();
    rt.write(rt.id("shown"), null, false);
    again();
    rt.write(rt.id("g"), "translate", [1, 1]);
    again();
    rt.write(rt.id("ink"), null, "#00ff00ff");
    again();
    rt.write(rt.id("c"), "fill", "#0000ffff");
    rt.write(rt.id("t"), "value", "there");
    again();
    rt.write(rt.id("shown"), null, true);
    again();
  });

  it("follows heads that come and go, and shapes that do", () => {
    const heads = load("heads");
    const h = redrawn(heads, heads.id("v"));
    heads.write(heads.id("on"), null, false);
    h.again();
    heads.write(heads.id("on"), null, true);
    h.again();
    const bounded = load("bounded");
    const b = redrawn(bounded, bounded.id("v"));
    for (const n of [5, 0, 2]) {
      bounded.write(bounded.id("n"), null, n);
      b.again();
    }
  });

  it("keeps the element of a shape that has not changed, and changes the one that has", () => {
    const rt = load("draw");
    const { svg, again } = redrawn(rt, rt.id("v"));
    const at = (name: string) => svg.querySelector(`[data-mtp-id="${rt.id(name)}"]`)!;
    const [c, b] = [at("c"), at("b")];
    rt.write(rt.id("c"), "x", 2);
    again();
    expect(at("c")).toBe(c);
    expect(at("c").getAttribute("cx")).toBe("2");
    expect(at("b")).toBe(b);
  });

  it("follows a write to any number in each example", () => {
    const docs = import.meta.glob("./data/examples/*.mtpc", { query: "?raw", import: "default", eager: true });
    expect(Object.keys(docs).length).toBeGreaterThan(0);
    for (const raw of Object.values(docs)) {
      const rt = new Runtime(JSON.parse(raw as string) as Doc);
      const canvases = rt.objects.flatMap((o, i) => (o.kind === "canvas" ? [i] : []));
      const views = canvases.map((c) => redrawn(rt, c));
      // A few free numbers in each, each moved a little.
      const free = rt.objects
        .flatMap((o, i) =>
          Object.entries({ ...(o.value ? { "": o.value } : {}), ...(o.attrs ?? {}) }).map(([a, p]) => [i, a === "" ? null : a, p] as const),
        )
        .filter(([i, a, p]) => "free" in p && !p.fixed && typeof rt.value(i, a) === "number")
        .slice(0, 6);
      for (const [i, a] of free) {
        rt.write(i, a, (rt.value(i, a) as number) + 1);
        for (const v of views) v.again();
      }
    }
  });
});
