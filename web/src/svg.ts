// Draws a canvas as SVG. Scenes have y pointing up and SVG has y pointing down, so the whole
// scene is flipped once at the top, and text is flipped back so its letters stay upright.
import { Matrix, compose, translate } from "./matrix.ts";
import { cssColor, fontCss } from "./colors.ts";
import type { Expr } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

const NS = "http://www.w3.org/2000/svg";
const CONTAINERS = new Set(["root", "group", "motif"]);
const FLIP = new Matrix(1, 0, 0, 0, -1, 0);

/** The SVG's view box, and the matrix from scene coordinates to the SVG's user coordinates. */
export function viewOf(rt: Runtime, canvas: number): { box: [number, number, number, number]; toUser: Matrix } {
  const x = rt.value(canvas, "view-x") as number;
  const y = rt.value(canvas, "view-y") as number;
  const width = rt.value(canvas, "view-width") as number;
  const height = rt.value(canvas, "view-height") as number;
  const cx = x + width / 2;
  const cy = y + height / 2;
  const view = compose(translate(-cx, -cy), rt.value(canvas, "transform") as Matrix, translate(cx, cy));
  return { box: [x, -(y + height), width, height], toUser: FLIP.times(view) };
}

export function draw(rt: Runtime, canvas: number, svg?: SVGSVGElement): SVGSVGElement {
  const out = svg ?? (document.createElementNS(NS, "svg") as SVGSVGElement);
  out.replaceChildren();
  const { box, toUser } = viewOf(rt, canvas);
  out.setAttribute("viewBox", box.join(" "));
  drawBackground(rt, canvas, out);
  const top = document.createElementNS(NS, "g");
  top.setAttribute("transform", toUser.svg());
  const view = rt.obj(canvas);
  (view.shows ?? []).forEach((member, k) => {
    const when = (view.when as (Expr | null)[] | undefined)?.[k];
    if (when === null || when === undefined || rt.eval(when, null, {})) drawObject(rt, member, top);
  });
  out.appendChild(top);
  return out;
}

function drawObject(rt: Runtime, i: number, into: Element): void {
  const kind = rt.kind(i);
  if (CONTAINERS.has(kind)) {
    for (const member of rt.obj(i).members ?? []) drawObject(rt, member, into);
    return;
  }
  if (kind === "text") {
    // A text in the middle of changing is drawn twice: the old one fading out, the new one in.
    const morph = rt.morphs.get(i);
    if (morph) into.appendChild(text(rt, i, morph[0], 1 - morph[1]));
    into.appendChild(text(rt, i, String(rt.value(i, "value")), morph ? morph[1] : 1));
    return;
  }
  const el = outline(rt, i);
  if (!el) return;
  el.setAttribute("transform", rt.shape(i).svg());
  el.setAttribute("data-mtp-id", String(i));
  paint(rt, i, el, kind === "line", 1);
  into.appendChild(el);
}

function text(rt: Runtime, i: number, value: string, fade: number): Element {
  const el = document.createElementNS(NS, "text") as SVGElement;
  el.setAttribute("font-size", String(rt.value(i, "font-size")));
  setFont(rt, i, el);
  el.textContent = value;
  el.setAttribute("transform", rt.shape(i).times(FLIP).svg());
  el.setAttribute("data-mtp-id", String(i));
  paint(rt, i, el, false, fade);
  return el;
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
      return el("rect", { x: 0, y: 0, width: v("width"), height: v("height"), rx: v("rx") ?? 0, ry: v("ry") ?? 0 });
    case "ellipse":
      return el("ellipse", { rx: v("rx"), ry: v("ry") });
    case "line":
      return el("line", { x1: v("x1"), y1: v("y1"), x2: v("x2"), y2: v("y2") });
    case "triangle": {
      const corners = [v("a"), v("b"), v("c")] as number[][];
      return el("polygon", { points: corners.map((p) => p.join(",")).join(" ") });
    }
    default:
      return null;
  }
}

// Opacity multiplies down the motifs and into each paint's own opacity, as in matplotlib.
function paint(rt: Runtime, i: number, el: Element, noFill: boolean, fade: number): void {
  const opacity = rt.opacity(i) * fade;
  const fill = noFill ? "none" : rt.value(i, "fill");
  setPaint(el, "fill", fill);
  if (fill !== "none") el.setAttribute("fill-opacity", String(rt.value(i, "fill-opacity") * opacity));
  const stroke = rt.value(i, "stroke");
  setPaint(el, "stroke", stroke);
  if (stroke !== "none") {
    el.setAttribute("stroke-width", String(rt.value(i, "stroke-width")));
    el.setAttribute("stroke-opacity", String(rt.value(i, "stroke-opacity") * opacity));
  }
}

// Through style, since the parts may be tokens (var()).
function setFont(rt: Runtime, i: number, el: SVGElement): void {
  for (const [property, css] of fontCss((attr) => rt.value(i, attr))) el.style.setProperty(property, css);
}

// Through style rather than attributes, since only CSS reads var() and color-mix().
function setPaint(el: Element, property: string, value: unknown): void {
  (el as SVGElement).style.setProperty(property, value === "none" ? "none" : cssColor(value));
}

// SVG has no background of its own, so the scene's background is the SVG element's CSS
// background: it fills the whole element, including any bands the page leaves around the view
// box, and the canvas transform does not move it.
function drawBackground(rt: Runtime, canvas: number, svg: SVGSVGElement): void {
  // The scene the canvas shows: the root above any of its members.
  let root = rt.obj(canvas).shows?.[0];
  while (root !== undefined && rt.parent(root) !== null) root = rt.parent(root) ?? undefined;
  const background = root === undefined ? undefined : rt.value(root, "background");
  if (background === undefined || background === "none") svg.style.removeProperty("background-color");
  else svg.style.setProperty("background-color", cssColor(background));
}
