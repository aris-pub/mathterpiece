import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Doc, Obj } from "../src/doc.ts";
import { Runtime } from "../src/runtime.ts";
import { draw } from "../src/svg.ts";

const style = {
  transform: [1, 0, 0, 0, 1, 0],
  x: 0,
  y: 0,
  fill: "red",
  stroke: "none",
  "stroke-width": 1,
  opacity: 1,
  "fill-opacity": 1,
  "stroke-opacity": 1,
};

// A canvas (id 0) showing a root (id 1) that holds the given shapes.
function scene(shapes: Omit<Obj, "id" | "parent">[], view: Record<string, unknown> = {}): Runtime {
  const members = shapes.map((_, k) => k + 2);
  const objects: Obj[] = [
    {
      id: 0,
      kind: "canvas",
      name: "view",
      attrs: { "view-x": 0, "view-y": 0, "view-width": 10, "view-height": 5, transform: style.transform, ...view },
      shows: [1],
    },
    { id: 1, kind: "root", name: "s", attrs: { transform: style.transform }, members },
    ...shapes.map((s, k) => ({ ...s, id: k + 2, parent: 1 }) as Obj),
  ];
  const doc: Doc = { mtp: 1, objects, functions: {}, names: {}, depends: {} };
  return new Runtime(doc);
}

const shape = (kind: string, attrs: Record<string, unknown>) => ({
  kind,
  name: null,
  attrs: { ...style, ...attrs },
});

// Where a point in an element's own coordinates lands in the SVG's user space.
function place(el: Element, x: number, y: number): [number, number] {
  const chain: string[] = [];
  for (let e: Element | null = el; e && e.tagName !== "svg"; e = e.parentElement) {
    const t = e.getAttribute("transform");
    if (t) chain.unshift(t);
  }
  let p: [number, number] = [x, y];
  for (const t of chain.reverse()) {
    const n = (t.match(/-?[\d.e+-]+/g) ?? []).map(Number);
    if (t.startsWith("scale")) p = [p[0] * (n[0] ?? 1), p[1] * (n[1] ?? n[0] ?? 1)];
    else {
      const [a = 1, b = 0, c = 0, d = 1, e = 0, f = 0] = n;
      p = [a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f];
    }
  }
  return p;
}

describe("the canvas", () => {
  it("shows the view's box, with y pointing up", () => {
    const svg = draw(scene([shape("circle", { x: 2, y: 4, r: 1 })]), 0);
    expect(svg.getAttribute("viewBox")).toBe("0 -5 10 5");
    const [x, y] = place(svg.querySelector("circle")!, 0, 0);
    expect(x).toBeCloseTo(2);
    expect(y).toBeCloseTo(-4);
  });

  it("turns the view about its center", () => {
    const svg = draw(scene([shape("circle", { x: 6, y: 2.5, r: 1 })], { transform: [0, -1, 0, 1, 0, 0] }), 0);
    const [x, y] = place(svg.querySelector("circle")!, 0, 0);
    expect(x).toBeCloseTo(5);
    expect(y).toBeCloseTo(-3.5);
  });
});

describe("the scene's background", () => {
  function withBackground(background: unknown, view: Record<string, unknown> = {}) {
    const rt = scene([shape("circle", { r: 1 })], view);
    (rt.obj(1).attrs as Record<string, unknown>).background = background;
    return draw(rt, 0);
  }

  it("is the SVG's CSS background, so it fills the whole element and nothing is drawn for it", () => {
    const svg = withBackground("#f7f3eaff");
    expect(svg.style.getPropertyValue("background-color")).toBe("#f7f3eaff");
    expect(svg.querySelector("rect")).toBeNull();
  });

  it("is cleared when it is none", () => {
    const rt = scene([shape("circle", { r: 1 })]);
    const attrs = rt.obj(1).attrs as Record<string, unknown>;
    attrs.background = "#000000ff";
    const svg = draw(rt, 0);
    attrs.background = "none";
    rt.refresh();
    draw(rt, 0, svg);
    expect(svg.style.getPropertyValue("background-color")).toBe("");
  });
});

describe("shapes", () => {
  it("draws a circle around its own origin, placed by its transform", () => {
    const c = draw(scene([shape("circle", { r: 2, fill: "#00ff00", "fill-opacity": 0.5, opacity: 0.5 })]), 0)
      .querySelector("circle")!;
    expect(c.getAttribute("r")).toBe("2");
    expect(c.style.getPropertyValue("fill")).toBe("#00ff00");
    expect(c.getAttribute("fill-opacity")).toBe("0.25");
    expect(c.style.getPropertyValue("stroke")).toBe("none");
  });

  it("draws rects from their corner", () => {
    const r = draw(scene([shape("rect", { width: 3, height: 2 })]), 0).querySelector("rect")!;
    expect([r.getAttribute("width"), r.getAttribute("height")]).toEqual(["3", "2"]);
    expect([r.getAttribute("x"), r.getAttribute("y")]).toEqual(["0", "0"]);
  });

  it("draws ellipses, lines and triangles", () => {
    const svg = draw(
      scene([
        shape("ellipse", { rx: 2, ry: 1 }),
        shape("line", { x1: 0, y1: 0, x2: 3, y2: 4, stroke: "blue", "stroke-width": 0.1 }),
        shape("triangle", { a: [0, 0], b: [1, 0], c: [0, 1] }),
      ]),
      0,
    );
    expect(svg.querySelector("ellipse")?.getAttribute("rx")).toBe("2");
    const line = svg.querySelector("line")!;
    expect(line.getAttribute("x2")).toBe("3");
    expect(line.getAttribute("stroke-width")).toBe("0.1");
    expect(svg.querySelector("polygon")?.getAttribute("points")).toBe("0,0 1,0 0,1");
  });

  it("keeps draw order", () => {
    const svg = draw(scene([shape("rect", { width: 1, height: 1 }), shape("circle", { r: 1 })]), 0);
    expect([...svg.querySelectorAll("rect, circle")].map((e) => e.tagName)).toEqual(["rect", "circle"]);
  });

  it("draws text upright", () => {
    const t = draw(scene([shape("text", { x: 1, y: 2, value: "hi", "font-size": 0.5 })]), 0).querySelector("text")!;
    expect(t.textContent).toBe("hi");
    expect(t.getAttribute("font-size")).toBe("0.5");
    const [, top] = place(t, 0, -1);
    const [, base] = place(t, 0, 0);
    expect(top).toBeLessThan(base);
  });
});

describe("text in the middle of changing", () => {
  it("draws the old text fading out and the new one fading in", () => {
    const rt = scene([shape("text", { value: "new", "font-size": 1, "fill-opacity": 0.8 })]);
    rt.morphs.set(2, ["old", 0.25]);
    const texts = [...draw(rt, 0).querySelectorAll("text")];
    expect(texts.map((t) => t.textContent)).toEqual(["old", "new"]);
    const [old, current] = texts.map((t) => Number(t.getAttribute("fill-opacity")));
    expect(old).toBeCloseTo(0.6);
    expect(current).toBeCloseTo(0.2);
  });
});

describe("every example", () => {
  // Vitest runs from web/; under happy-dom, import.meta.url is not a file URL.
  const dir = join(process.cwd(), "test", "data", "examples");
  const examples = readdirSync(dir).filter((f) => f.endsWith(".json"));

  it.each(examples)("%s draws every shape it shows", (file) => {
    const doc = JSON.parse(readFileSync(join(dir, file), "utf8")) as Doc;
    const rt = new Runtime(doc, () => 0.5);
    for (const canvas of doc.objects.filter((o) => o.kind === "canvas")) {
      const svg = draw(rt, canvas.id);
      expect(svg.querySelectorAll("circle, rect, ellipse, line, polygon, text").length).toBe(
        countShapes(doc, canvas.shows ?? []),
      );
    }
  });
});

function countShapes(doc: Doc, ids: number[]): number {
  let n = 0;
  for (const id of ids) {
    const o = doc.objects[id]!;
    n += o.members ? countShapes(doc, o.members) : 1;
  }
  return n;
}
