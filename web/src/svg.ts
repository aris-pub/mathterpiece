// Draws a canvas as SVG. Scenes have y pointing up and SVG has y pointing down, so the whole
// scene is flipped once at the top, and text is flipped back so its letters stay upright.
import { Matrix, compose, translate } from "./matrix.ts";
import type { Runtime } from "./runtime.ts";

const NS = "http://www.w3.org/2000/svg";
const CONTAINERS = new Set(["root", "group", "motif"]);
const FLIP = new Matrix(1, 0, 0, 0, -1, 0);

export function draw(rt: Runtime, canvas: number, svg?: SVGSVGElement): SVGSVGElement {
  const out = svg ?? (document.createElementNS(NS, "svg") as SVGSVGElement);
  out.replaceChildren();
  const x = rt.value(canvas, "view-x") as number;
  const y = rt.value(canvas, "view-y") as number;
  const width = rt.value(canvas, "view-width") as number;
  const height = rt.value(canvas, "view-height") as number;
  out.setAttribute("viewBox", `${x} ${-(y + height)} ${width} ${height}`);
  const cx = x + width / 2;
  const cy = y + height / 2;
  const view = compose(translate(-cx, -cy), rt.value(canvas, "transform") as Matrix, translate(cx, cy));
  const top = document.createElementNS(NS, "g");
  top.setAttribute("transform", FLIP.times(view).svg());
  for (const member of rt.obj(canvas).shows ?? []) drawObject(rt, member, top);
  out.appendChild(top);
  return out;
}

function drawObject(rt: Runtime, i: number, into: Element): void {
  const kind = rt.kind(i);
  if (CONTAINERS.has(kind)) {
    for (const member of rt.obj(i).members ?? []) drawObject(rt, member, into);
    return;
  }
  const el = outline(rt, i);
  if (!el) return;
  const placed = kind === "text" ? rt.shape(i).times(FLIP) : rt.shape(i);
  el.setAttribute("transform", placed.svg());
  paint(rt, i, el, kind === "line");
  into.appendChild(el);
}

// Each shape drawn around its own origin; rt.shape places it.
function outline(rt: Runtime, i: number): Element | null {
  const v = (attr: string) => rt.value(i, attr);
  const el = (tag: string, attrs: Record<string, unknown>) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, value] of Object.entries(attrs)) e.setAttribute(k, String(value));
    return e;
  };
  switch (rt.kind(i)) {
    case "circle":
      return el("circle", { r: v("r") });
    case "rect":
      return el("rect", { x: 0, y: 0, width: v("width"), height: v("height") });
    case "ellipse":
      return el("ellipse", { rx: v("rx"), ry: v("ry") });
    case "line":
      return el("line", { x1: v("x1"), y1: v("y1"), x2: v("x2"), y2: v("y2") });
    case "triangle": {
      const corners = [v("a"), v("b"), v("c")] as number[][];
      return el("polygon", { points: corners.map((p) => p.join(",")).join(" ") });
    }
    case "text": {
      const t = el("text", { "font-size": v("font-size") });
      t.textContent = String(v("value"));
      return t;
    }
    default:
      return null;
  }
}

// Opacity multiplies down the motifs and into each paint's own opacity, as in matplotlib.
function paint(rt: Runtime, i: number, el: Element, noFill: boolean): void {
  const opacity = rt.opacity(i);
  const fill = noFill ? "none" : String(rt.value(i, "fill"));
  el.setAttribute("fill", fill);
  if (fill !== "none") el.setAttribute("fill-opacity", String(rt.value(i, "fill-opacity") * opacity));
  const stroke = String(rt.value(i, "stroke"));
  el.setAttribute("stroke", stroke);
  if (stroke !== "none") {
    el.setAttribute("stroke-width", String(rt.value(i, "stroke-width")));
    el.setAttribute("stroke-opacity", String(rt.value(i, "stroke-opacity") * opacity));
  }
}
