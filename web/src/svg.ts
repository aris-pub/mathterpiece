// Draws a canvas as SVG. The scene has y pointing up and SVG has y pointing down, so the whole
// scene is flipped once at the top, and text is flipped back so its letters stay upright. Each
// group and instance is a <g> with its own frame (docs/reference.md, "Coordinates").
import { apply, compose } from "./builtins.ts";
import type { Expr } from "./doc.ts";
import { isBound, whenItems } from "./doc.ts";
import type { Runtime } from "./runtime.ts";

const NS = "http://www.w3.org/2000/svg";
const FLIP = [1, 0, 0, -1, 0, 0];

function matrix(m: number[]): string {
  return `matrix(${m.join(" ")})`;
}

/** The SVG's view box, and the transform from scene coordinates to the SVG's own. */
export function viewOf(rt: Runtime, canvas: number): { box: number[]; toUser: number[] } {
  const v = (a: string) => rt.value(canvas, a) as number;
  // The view box is given in the scene's own coordinates, which the scene's transform takes to
  // where they are drawn (mtp-y0gh): the region shown is the box around its corners there.
  const own = sceneTransform(rt);
  const [x0, y0, w0, h0] = [v("x"), v("y"), v("width"), v("height")];
  const corners = [
    [x0, y0],
    [x0 + w0, y0],
    [x0, y0 + h0],
    [x0 + w0, y0 + h0],
  ].map((c) => apply(own, c) as number[]);
  const x = Math.min(...corners.map((c) => c[0]!));
  const y = Math.min(...corners.map((c) => c[1]!));
  const width = Math.max(...corners.map((c) => c[0]!)) - x;
  const height = Math.max(...corners.map((c) => c[1]!)) - y;
  const cx = x + width / 2;
  const cy = y + height / 2;
  // A canvas's transform applies about the center of its view box.
  const t = rt.value(canvas, "transform") as number[];
  const view = compose([1, 0, 0, 1, -cx, -cy], t, [1, 0, 0, 1, cx, cy]);
  return { box: [x, -(y + height), width, height], toUser: compose(own, view, FLIP) };
}

function sceneTransform(rt: Runtime): number[] {
  const scene = rt.objects.findIndex((o) => o.kind === "scene");
  return scene >= 0 && rt.objects[scene]!.attrs?.transform ? (rt.value(scene, "transform") as number[]) : [1, 0, 0, 1, 0, 0];
}

/**
 * How far the reader has zoomed (scale) and panned (dx, dy, in the SVG's own units) a canvas:
 * the canvas's own state, which writes nothing in the model.
 */
export interface Look {
  scale: number;
  dx: number;
  dy: number;
}

/** The view box the reader sees: the author's, zoomed about its center and moved. */
export function lookBox(box: number[], look?: Look): number[] {
  if (!look) return box;
  const [x, y, w, h] = box as [number, number, number, number];
  const [width, height] = [w / look.scale, h / look.scale];
  return [x + w / 2 + look.dx - width / 2, y + h / 2 + look.dy - height / 2, width, height];
}

/**
 * Draws a canvas: what it shows, and what each of its when items shows while it holds. visible
 * says how visible the k-th when item's shapes are, from 0 (not drawn) to 1, for a canvas fading
 * them in or out; by default, 1 while its condition holds and 0 otherwise.
 */
export function draw(
  rt: Runtime,
  canvas: number,
  svg?: SVGSVGElement,
  visible?: (k: number) => number,
  look?: Look,
): SVGSVGElement {
  const out = svg ?? (document.createElementNS(NS, "svg") as SVGSVGElement);
  out.replaceChildren();
  const { box: authors, toUser } = viewOf(rt, canvas);
  const box = lookBox(authors, look);
  out.setAttribute("viewBox", box.join(" "));
  const view = rt.objects[canvas]!;
  const shows = view.shows ?? [];
  const when = whenItems(view);
  const levels = when.map(([cond], k) => (visible ? visible(k) : rt.evaluate(cond) ? 1 : 0));
  background(rt, shows.flatMap((s) => (typeof s === "number" ? [s] : s[1])), out);
  const top = document.createElementNS(NS, "g");
  top.setAttribute("transform", matrix(toUser));
  // Until the SVG is on the page its width is 0; a canvas redraws once it has one.
  const width = out.getBoundingClientRect?.().width || 640;
  const unitsPerPx = box[2]! / width;
  let k = 0;
  for (const shown of shows) {
    if (typeof shown === "number") {
      drawObject(rt, shown, top, unitsPerPx);
      continue;
    }
    const ids = shown[1];
    const level = levels[k++]!;
    if (level <= 0) continue;
    let into: Element = top;
    if (level < 1) {
      // A canvas fades what its when items show and hide along its move (reference.md).
      into = document.createElementNS(NS, "g");
      into.setAttribute("data-mtp-fade", "");
      into.setAttribute("opacity", String(level));
      top.appendChild(into);
    }
    for (const i of ids) drawObject(rt, i, into, unitsPerPx);
  }
  out.appendChild(top);
  return out;
}

// SVG has no background of its own, so the scene's background is the SVG element's.
function background(rt: Runtime, shown: number[], svg: SVGSVGElement): void {
  let root: number | undefined = shown[0];
  while (root !== undefined && rt.parent(root) !== null) root = rt.parent(root)!;
  const bg = root === undefined || rt.objects[root]!.kind !== "scene" ? null : rt.value(root, "background");
  if (bg === null) svg.style.removeProperty("background-color");
  else svg.style.setProperty("background-color", paintCss(rt, root!, "background"));
}

function drawObject(rt: Runtime, i: number, into: Element, unitsPerPx: number): void {
  const o = rt.objects[i]!;
  if (o.kind === "scene") {
    for (const m of o.members ?? []) drawObject(rt, m, into, unitsPerPx);
    return;
  }
  if (absent(rt, i)) return;
  if (o.kind === "group" || o.kind === "instance") {
    const g = document.createElementNS(NS, "g");
    g.setAttribute("transform", matrix(rt.local(i, true)));
    g.setAttribute("data-mtp-id", String(i));
    if (o.clip !== undefined) clipTo(rt, o.clip, g, unitsPerPx);
    for (const m of o.members ?? []) drawObject(rt, m, g, unitsPerPx);
    into.appendChild(g);
    return;
  }
  const el = shapeElement(rt, i, unitsPerPx);
  el.setAttribute("data-mtp-id", String(i));
  const own = rt.local(i);
  if (o.kind === "text") {
    const [x, y] = rt.value(i, "pos") as number[];
    // Text is placed at its anchor and flipped back upright there.
    el.setAttribute("transform", matrix(compose(FLIP, [1, 0, 0, 1, x!, y!], own)));
  } else if (!own.every((v, k) => v === [1, 0, 0, 1, 0, 0][k])) {
    el.setAttribute("transform", matrix(own));
  }
  paint(rt, i, el);
  into.appendChild(el);
}

// A shape declared T|none is not drawn when it is absent: while its exists-when does not hold, or
// when an attribute it needs is none.
function absent(rt: Runtime, i: number): boolean {
  if (!rt.exists(i)) return true;
  const o = rt.objects[i]!;
  return Object.entries(o.attrs ?? {}).some(
    ([attr, p]) => attr !== "fill" && attr !== "stroke" && attr !== "exists" && p.type && rt.value(i, attr) === null,
  );
}

// Several canvases may draw the same container on one page, so each clip path gets its own id.
let clips = 0;

/**
 * Clips a container's <g> to its clip shape (mtp-un2f). The clip path sits inside the <g>, in its
 * frame; SVG then also keeps the pointer from what it cuts off.
 */
function clipTo(rt: Runtime, clip: number, g: Element, unitsPerPx: number): void {
  const path = document.createElementNS(NS, "clipPath");
  path.id = `mtp-clip-${++clips}`;
  const el = shapeElement(rt, clip, unitsPerPx);
  const own = rt.local(clip);
  if (!own.every((v, k) => v === [1, 0, 0, 1, 0, 0][k])) el.setAttribute("transform", matrix(own));
  path.appendChild(el);
  g.appendChild(path);
  g.setAttribute("clip-path", `url(#${path.id})`);
}

function shapeElement(rt: Runtime, i: number, unitsPerPx: number): Element {
  const v = (attr: string) => rt.value(i, attr) as number;
  const el = (tag: string, attrs: Record<string, unknown>) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, value] of Object.entries(attrs)) e.setAttribute(k, String(value));
    return e;
  };
  const o = rt.objects[i]!;
  switch (o.kind) {
    case "circle":
      return el("circle", { cx: v("x"), cy: v("y"), r: v("r") });
    case "rect":
      // A rect's position is its center.
      return el("rect", {
        x: v("x") - v("width") / 2,
        y: v("y") - v("height") / 2,
        width: v("width"),
        height: v("height"),
        rx: v("rx"),
        ry: v("ry"),
      });
    case "ellipse":
      return el("ellipse", { cx: v("x"), cy: v("y"), rx: v("rx"), ry: v("ry") });
    case "line": {
      const [x1, y1] = rt.value(i, "from") as number[];
      const [x2, y2] = rt.value(i, "to") as number[];
      return el("line", { x1, y1, x2, y2 });
    }
    case "triangle": {
      const corners = ["a", "b", "c"].map((c) => (rt.value(i, c) as number[]).join(","));
      return el("polygon", { points: corners.join(" ") });
    }
    case "polyline":
    case "polygon": {
      const points = (rt.value(i, "points") as number[][]).map((p) => p.join(","));
      return el(o.kind, { points: points.join(" ") });
    }
    case "text":
      return text(rt, i, unitsPerPx);
    default:
      throw new Error(`cannot draw a ${o.kind}`);
  }
}

function text(rt: Runtime, i: number, unitsPerPx: number): Element {
  const el = document.createElementNS(NS, "text") as SVGElement;
  el.textContent = String(rt.value(i, "value"));
  const anchor = rt.value(i, "halign");
  if (anchor === "middle" || anchor === "end") el.setAttribute("text-anchor", anchor as string);
  const baseline = { top: "hanging", middle: "central", bottom: "text-after-edge" }[rt.value(i, "valign") as string];
  if (baseline) el.setAttribute("dominant-baseline", baseline);
  const font = rt.value(i, "font") as Record<string, unknown>;
  // Font sizes are in screen pixels, whatever the view box.
  el.setAttribute("font-size", String((font.size as number) * unitsPerPx));
  const variable = tokenOf(rt, i, "font");
  for (const part of ["family", "style", "weight"]) {
    const own = font[part];
    const css = variable ? `var(--mtp-${variable}-${part}${own === null ? "" : `, ${String(own)}`})` : own;
    if (css !== null && css !== undefined) el.style.setProperty(`font-${part}`, String(css));
  }
  return el;
}

// Fill, stroke and their opacities mirror SVG: a color's alpha, fill-opacity and stroke-opacity
// multiply, and opacity fades the drawn shape as a whole.
function paint(rt: Runtime, i: number, el: Element): void {
  const s = el as SVGElement;
  // A line and a polyline are paths with no inside, so their fill is never drawn.
  const open = ["line", "polyline"].includes(rt.objects[i]!.kind);
  s.style.setProperty("fill", open ? "none" : paintCss(rt, i, "fill"));
  s.style.setProperty("stroke", paintCss(rt, i, "stroke"));
  el.setAttribute("fill-opacity", String(rt.value(i, "fill-opacity")));
  el.setAttribute("stroke-opacity", String(rt.value(i, "stroke-opacity")));
  el.setAttribute("opacity", String(rt.value(i, "opacity")));
  el.setAttribute("stroke-width", String(rt.value(i, "stroke-width")));
  const dash = rt.value(i, "dash") as number[];
  el.setAttribute("stroke-dasharray", dash.length ? dash.join(" ") : "none");
  el.setAttribute("stroke-dashoffset", String(rt.value(i, "dash-offset")));
  el.setAttribute("stroke-linecap", String(rt.value(i, "line-cap")));
  el.setAttribute("stroke-linejoin", String(rt.value(i, "line-join")));
  // Stroke widths and dashes are in screen pixels, whatever the view box.
  el.setAttribute("vector-effect", "non-scaling-stroke");
}

/** A paint as CSS: none, a color, or one computed from tokens through their CSS variables (docs/mtpc.md). */
export function paintCss(rt: Runtime, i: number, attr: string): string {
  const v = rt.value(i, attr);
  if (v === null) return "none";
  return rt.css(i, attr) ?? String(v);
}

// The name of the token variable an attribute reads directly, if it does.
function tokenOf(rt: Runtime, i: number, attr: string): string | null {
  const p = rt.objects[i]!.attrs?.[attr];
  if (!p || !isBound(p)) return null;
  const e = p.bound as Expr;
  if (e[0] !== "read" || e[3] !== null) return null;
  const v = rt.objects[e[2] as number]!;
  return v.kind === "variable" && v.token ? v.name : null;
}
