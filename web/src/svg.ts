// Draws a canvas as SVG. The scene has y pointing up and SVG has y pointing down, so the whole
// scene is flipped once at the top, and text is flipped back so its letters stay upright. Each
// group and instance is a <g> with its own frame (docs/reference.md, "Coordinates").
import { arcPath, ringPath } from "./arc.ts";
import { Ref, apply, compose } from "./builtins.ts";
import type { Expr } from "./doc.ts";
import { isBound, itemsOf } from "./doc.ts";
import { type Runtime, cssVariable } from "./runtime.ts";

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
 * Draws a canvas: what it shows, and the shapes each of its items gives. shownBy gives the k-th
 * item's shapes and how visible each is, from 0 (not drawn) to 1, for a canvas toggling them; by
 * default, the shapes the item gives now, each fully visible.
 */
export function draw(
  rt: Runtime,
  canvas: number,
  svg?: SVGSVGElement,
  shownBy?: (k: number) => [number, number][],
  look?: Look,
): SVGSVGElement {
  const out = svg ?? (document.createElementNS(NS, "svg") as SVGSVGElement);
  out.replaceChildren();
  const { box: authors, toUser } = viewOf(rt, canvas);
  const box = lookBox(authors, look);
  out.setAttribute("viewBox", box.join(" "));
  const view = rt.objects[canvas]!;
  const shows = view.shows ?? [];
  const items = itemsOf(view);
  const shapes = items.map((item, k): [number, number][] =>
    shownBy ? shownBy(k) : shapesOf(rt.evaluate(item)).map((id) => [id, 1]),
  );
  let j = 0;
  background(rt, shows.flatMap((s) => (typeof s === "number" ? [s] : shapes[j++]!.map(([id]) => id))), out);
  const top = document.createElementNS(NS, "g");
  top.setAttribute("transform", matrix(toUser));
  const unitsPerPx = unitsPerPxOf(out, box);
  let k = 0;
  for (const shown of shows) {
    if (typeof shown === "number") {
      drawObject(rt, shown, top, unitsPerPx);
      continue;
    }
    for (const [id, level] of shapes[k++]!) {
      if (level <= 0) continue;
      let into: Element = top;
      if (level < 1) {
        // A canvas toggles a shape, showing or hiding it, over its toggle-duration.
        into = document.createElementNS(NS, "g");
        into.setAttribute("data-mtp-toggle", "");
        into.setAttribute("opacity", String(level));
        top.appendChild(into);
      }
      drawObject(rt, id, into, unitsPerPx);
    }
  }
  out.appendChild(top);
  return out;
}

/** The ids of the shapes a canvas item gives: one shape, none, or a list of them. */
export function shapesOf(v: unknown): number[] {
  if (v instanceof Ref) return [v.id];
  if (Array.isArray(v)) return v.flatMap(shapesOf);
  return [];
}

// Until the SVG is on the page its width is 0; a canvas redraws once it has one.
function unitsPerPxOf(svg: SVGSVGElement, box: number[]): number {
  return box[2]! / (svg.getBoundingClientRect?.().width || 640);
}

/**
 * Zooms a drawn canvas to a new look, as draw would draw it, without drawing its shapes again:
 * only the view box and what is sized in screen pixels change. Strokes need nothing, since SVG
 * keeps their widths on screen itself.
 */
export function zoom(rt: Runtime, canvas: number, svg: SVGSVGElement, look: Look): void {
  const box = lookBox(viewOf(rt, canvas).box, look);
  svg.setAttribute("viewBox", box.join(" "));
  const unitsPerPx = unitsPerPxOf(svg, box);
  for (const el of svg.querySelectorAll("text[data-mtp-id]")) {
    el.setAttribute("font-size", fontSize(rt, Number(el.getAttribute("data-mtp-id")), unitsPerPx));
  }
  for (const m of svg.querySelectorAll("marker[data-mtp-head-px]")) {
    const size = String(Number(m.getAttribute("data-mtp-head-px")) * unitsPerPx);
    m.setAttribute("markerWidth", size);
    m.setAttribute("markerHeight", size);
  }
}

// Font sizes are in screen pixels, whatever the view box.
function fontSize(rt: Runtime, i: number, unitsPerPx: number): string {
  return String(((rt.value(i, "font") as Record<string, unknown>).size as number) * unitsPerPx);
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
  heads(rt, i, el, into, unitsPerPx);
  into.appendChild(el);
}

// A head is this many stroke widths long (mtp-brs), times the shape's head-size.
const HEAD_LENGTH = 5;
// Several canvases may draw the same shape on one page, so each head gets its own id.
let headIds = 0;

// Each kind, drawn in a 10 by 10 box with the line coming in from the left along y = 5. refX is
// the point put at the line's end: a little short of the tip, so the head covers the line's end.
const HEAD_SHAPES: Record<string, { refX: number; tag: string; attrs: Record<string, string>; stroked: boolean }> = {
  dart: { refX: 7.5, tag: "path", attrs: { d: "M0,0 L10,5 L0,10 L3,5 Z" }, stroked: false },
  curved: { refX: 7.5, tag: "path", attrs: { d: "M0,0 Q6,4.3 10,5 Q6,5.7 0,10 L2.5,5 Z" }, stroked: false },
  open: { refX: 9, tag: "path", attrs: { d: "M1,1 L9,5 L1,9" }, stroked: true },
  bar: { refX: 5, tag: "path", attrs: { d: "M5,0 L5,10" }, stroked: true },
  dot: { refX: 5, tag: "circle", attrs: { cx: "5", cy: "5", r: "3.5" }, stroked: false },
};

/**
 * The heads at a line's, a polyline's or an arc's ends, as SVG markers in its stroke (mtp-brs).
 * Its stroke width is in screen pixels, which a marker does not follow, so each head is sized in
 * the view's units from its length in pixels, and zoom sizes it again.
 */
function heads(rt: Runtime, i: number, el: Element, into: Element, unitsPerPx: number): void {
  if (!["line", "polyline", "arc"].includes(rt.objects[i]!.kind)) return;
  const stroke = paintCss(rt, i, "stroke");
  if (stroke === "none") return;
  const px = HEAD_LENGTH * (rt.value(i, "stroke-width") as number) * (rt.value(i, "head-size") as number);
  for (const end of ["start", "end"] as const) {
    const shape = HEAD_SHAPES[rt.value(i, `head-${end}`) as string];
    if (!shape) continue;
    const marker = document.createElementNS(NS, "marker");
    marker.id = `mtp-head-${++headIds}`;
    for (const [k, v] of Object.entries({
      viewBox: "0 0 10 10",
      markerUnits: "userSpaceOnUse",
      markerWidth: String(px * unitsPerPx),
      markerHeight: String(px * unitsPerPx),
      refX: String(shape.refX),
      refY: "5",
      // The start's head points back, away from the line, as the end's points forward.
      orient: end === "start" ? "auto-start-reverse" : "auto",
      "data-mtp-head-px": String(px),
    })) {
      marker.setAttribute(k, v);
    }
    const mark = document.createElementNS(NS, shape.tag) as SVGElement;
    for (const [k, v] of Object.entries(shape.attrs)) mark.setAttribute(k, v);
    mark.style.setProperty("fill", shape.stroked ? "none" : stroke);
    mark.style.setProperty("stroke", shape.stroked ? stroke : "none");
    if (shape.stroked) {
      // As wide as the line itself: the box is a tenth of the head's length on each side.
      mark.setAttribute("stroke-width", String(10 / HEAD_LENGTH));
      mark.setAttribute("stroke-linecap", "round");
      mark.setAttribute("stroke-linejoin", "round");
    }
    const opacity = String(rt.value(i, "stroke-opacity"));
    mark.setAttribute(shape.stroked ? "stroke-opacity" : "fill-opacity", opacity);
    marker.appendChild(mark);
    into.appendChild(marker);
    el.setAttribute(`marker-${end}`, `url(#${marker.id})`);
  }
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
    case "arc":
      return el("path", { d: arcPath(v("x"), v("y"), v("r"), v("from"), v("to")) });
    case "ring":
      return el("path", { d: ringPath(v("x"), v("y"), v("r"), v("width"), v("from"), v("to")) });
    case "text":
      return text(rt, i, unitsPerPx);
    default:
      throw new Error(`cannot draw a ${o.kind}`);
  }
}

function text(rt: Runtime, i: number, unitsPerPx: number): Element {
  const el = document.createElementNS(NS, "text") as SVGElement;
  el.textContent = String(rt.value(i, "value"));
  // SVG would otherwise drop leading spaces and run spaces together; this keeps each one, and
  // shows a tab or a newline as a space.
  el.setAttributeNS("http://www.w3.org/XML/1998/namespace", "xml:space", "preserve");
  const anchor = rt.value(i, "halign");
  if (anchor === "middle" || anchor === "end") el.setAttribute("text-anchor", anchor as string);
  const baseline = { top: "hanging", middle: "central", bottom: "text-after-edge" }[rt.value(i, "valign") as string];
  if (baseline) el.setAttribute("dominant-baseline", baseline);
  const font = rt.value(i, "font") as Record<string, unknown>;
  el.setAttribute("font-size", fontSize(rt, i, unitsPerPx));
  const variable = tokenOf(rt, i, "font");
  for (const part of ["family", "style", "weight"]) {
    const css = variable === null ? font[part] : fontPartCss(rt, rt.id(variable), part);
    if (css !== null && css !== undefined) el.style.setProperty(`font-${part}`, String(css));
  }
  return el;
}

// Fill, stroke and their opacities mirror SVG: a color's alpha, fill-opacity and stroke-opacity
// multiply, and opacity fades the drawn shape as a whole.
function paint(rt: Runtime, i: number, el: Element): void {
  const s = el as SVGElement;
  // A line, a polyline and an arc are paths with no inside, so their fill is never drawn.
  const open = ["line", "polyline", "arc"].includes(rt.objects[i]!.kind);
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
/** A font token's part as CSS: its own variable, falling back to the font it reads the part
 * from, if any, and then to its value. */
function fontPartCss(rt: Runtime, id: number, part: string): string {
  const o = rt.objects[id]!;
  const link = o.links?.[part];
  const own = (rt.value(id, null) as Record<string, unknown>)[part];
  const fallback = link !== undefined ? fontPartCss(rt, link, part) : own === null ? null : String(own);
  return `var(${cssVariable(o.name!)}-${part}${fallback === null ? "" : `, ${fallback}`})`;
}

function tokenOf(rt: Runtime, i: number, attr: string): string | null {
  const p = rt.objects[i]!.attrs?.[attr];
  if (!p || !isBound(p)) return null;
  const e = p.bound as Expr;
  if (e[0] !== "read" || e[3] !== null) return null;
  const v = rt.objects[e[2] as number]!;
  return v.kind === "variable" && v.token ? v.name : null;
}
