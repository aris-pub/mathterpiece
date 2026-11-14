// Draws a canvas as SVG. The scene has y pointing up and SVG has y pointing down, so the whole
// scene is flipped once at the top, and text is flipped back so its letters stay upright. Each
// group and instance is a <g> with its own frame (docs/reference.md, "Coordinates").
import { arcPath, ringPath } from "./arc.ts";
import { Ref, apply, compose } from "./builtins.ts";
import { curvePath } from "./curve.ts";
import { drawnPart, outlineOf, outlinePath } from "./outline.ts";
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
 * An element as drawing wants it: its tag, attributes, style, text and children. A canvas is
 * drawn as these first, and the SVG on the page is then changed only where they differ from what
 * it shows, so a change to one shape does not make the browser lay out every other one again.
 */
interface Drawn {
  tag: string;
  attrs: Record<string, string>;
  style: Record<string, string>;
  children: Drawn[];
  text: string | null;
}

function node(tag: string, attrs: Record<string, unknown> = {}): Drawn {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(attrs)) out[k] = String(v);
  return { tag, attrs: out, style: {}, children: [], text: null };
}

/**
 * What a canvas keeps between drawings: each shape's elements, with the runtime's clock when
 * they were drawn. A shape is drawn again only once something it is drawn from has changed
 * since (Runtime.touchedAt), or the canvas's units a pixel have.
 */
export class DrawMemo {
  shapes = new Map<number, { at: number; drawn: Drawn[] }>();
  units = Number.NaN;
  /** The SVG's width on screen, when its canvas follows it as it changes: asking the page for it
   * while drawing would make the browser lay the page out first. */
  width: number | null = null;
}

/**
 * How a canvas draws the shapes that have an on-show or on-hide in it (mtp-7i3j): rt is what it
 * draws from, the scene with each stand-in in place of its shape. Such a shape is drawn as its
 * stand-in or its original, or not at all while hidden, and never faded by toggle-duration.
 */
export interface Showing {
  rt: Runtime;
  /** Whether the shape is one of them, or a container holding one. */
  around(id: number): boolean;
  governs(id: number): boolean;
  hidden(id: number): boolean;
  standIn(id: number): boolean;
}

interface Pass {
  rt: Runtime;
  showing: Showing | null;
  // Each drawing's marker and clip ids start with its SVG's own number.
  prefix: number;
  memo: DrawMemo | null;
}

// What each element on the page was last drawn as.
const DRAWN = new WeakMap<Element, Drawn>();
const prefixes = new WeakMap<SVGSVGElement, number>();
let svgs = 0;

/**
 * Draws a canvas: what it shows, and the shapes each of its items gives. shownBy gives the k-th
 * item's shapes and how visible each is, from 0 (not drawn) to 1, for a canvas toggling them; by
 * default, the shapes the item gives now, each fully visible. memo keeps what is drawn for the
 * next drawing of the same SVG.
 */
export function draw(
  rt: Runtime,
  canvas: number,
  svg?: SVGSVGElement,
  shownBy?: (k: number) => [number, number][],
  look?: Look,
  memo?: DrawMemo,
  showing?: Showing,
): SVGSVGElement {
  const out = svg ?? (document.createElementNS(NS, "svg") as SVGSVGElement);
  if (!prefixes.has(out)) prefixes.set(out, ++svgs);
  const { box: authors, toUser } = viewOf(rt, canvas);
  const box = lookBox(authors, look);
  setIfNew(out, "viewBox", box.join(" "));
  const view = rt.objects[canvas]!;
  const shows = view.shows ?? [];
  const items = itemsOf(view);
  const shapes = items.map((item, k): [number, number][] =>
    shownBy ? shownBy(k) : shapesOf(rt.evaluate(item)).map((id) => [id, 1]),
  );
  let j = 0;
  background(rt, shows.flatMap((s) => (typeof s === "number" ? [s] : shapes[j++]!.map(([id]) => id))), out);
  const top = node("g", { transform: matrix(toUser) });
  const unitsPerPx = unitsPerPxOf(out, box, memo?.width ?? undefined);
  if (memo && memo.units !== unitsPerPx) {
    memo.shapes.clear();
    memo.units = unitsPerPx;
  }
  const pass: Pass = { rt: showing?.rt ?? rt, showing: showing ?? null, prefix: prefixes.get(out)!, memo: memo ?? null };
  let k = 0;
  for (const shown of shows) {
    if (typeof shown === "number") {
      drawObject(pass, shown, top.children, unitsPerPx);
      continue;
    }
    for (const [id, level] of shapes[k++]!) {
      // Such an item is faded shape by shape, so its shapes with an on-show or on-hide are not.
      if (showing?.around(id)) {
        drawObject(pass, id, top.children, unitsPerPx, level);
        continue;
      }
      if (level <= 0) continue;
      let into = top.children;
      if (level < 1) {
        // A canvas toggles a shape, showing or hiding it, over its toggle-duration.
        const g = node("g", { "data-mtp-toggle": "", opacity: level });
        top.children.push(g);
        into = g.children;
      }
      drawObject(pass, id, into, unitsPerPx);
    }
  }
  placed = new Set();
  patchChildren(out, [top]);
  placed = new Set();
  return out;
}

function setIfNew(el: Element, attr: string, value: string): void {
  if (el.getAttribute(attr) !== value) el.setAttribute(attr, value);
}

/** The ids of the shapes a canvas item gives: one shape, none, or a list of them. */
export function shapesOf(v: unknown): number[] {
  if (v instanceof Ref) return [v.id];
  if (Array.isArray(v)) return v.flatMap(shapesOf);
  return [];
}

// Until the SVG is on the page its width is 0; a canvas redraws once it has one.
// A CSS length on a shape inside the SVG is in the view box's units, so a style sized in screen
// pixels multiplies by --mtp-unit, the units a pixel.
function unitsPerPxOf(svg: SVGSVGElement, box: number[], width?: number): number {
  const units = box[2]! / ((width ?? svg.getBoundingClientRect?.().width) || 640);
  if (svg.style.getPropertyValue("--mtp-unit") !== String(units)) svg.style.setProperty("--mtp-unit", String(units));
  return units;
}

// The page's SVG made to show what is wanted, keeping each element that is still wanted: an
// element drawn with a data-mtp-id is kept for the same shape, any other for the next one of its
// tag.
// spare finds an element kept elsewhere for a shape, by tag and id.
type Spare = (key: string) => Element | undefined;

function patchChildren(parent: Element, want: Drawn[], spare?: Spare): void {
  // Most often the elements are the ones wanted, in the same order: those are changed in place.
  const children = parent.children;
  let start = 0;
  for (; start < want.length && start < children.length; start++) {
    const el = children[start]!;
    const was = DRAWN.get(el);
    const d = want[start]!;
    if (!was || was.tag !== d.tag || was.attrs["data-mtp-id"] !== d.attrs["data-mtp-id"]) break;
    patch(el, d);
  }
  if (start === want.length && start === children.length) return;
  const keyed = new Map<string, Element[]>();
  const loose = new Map<string, Element[]>();
  // A shape a canvas starts or stops toggling moves out of or into the <g> that fades it, and a
  // shape partly drawn is inside a <g> too (data-mtp-drawn), so the shapes inside those are
  // kept as well.
  const inner = new Map<string, Element[]>();
  const add = (pool: Map<string, Element[]>, k: string, el: Element) => {
    const list = pool.get(k);
    if (list) list.push(el);
    else pool.set(k, [el]);
  };
  for (const el of Array.from(children).slice(start)) {
    const was = DRAWN.get(el);
    if (!was) continue;
    const id = was.attrs["data-mtp-id"];
    if (id === undefined) add(loose, was.tag, el);
    else add(keyed, `${was.tag}#${id}`, el);
    if (was.attrs["data-mtp-toggle"] === undefined && was.attrs["data-mtp-drawn"] === undefined) continue;
    for (const c of Array.from(el.children)) {
      const w = DRAWN.get(c);
      const cid = w?.attrs["data-mtp-id"];
      if (cid !== undefined) add(inner, `${w!.tag}#${cid}`, c);
    }
  }
  const find: Spare = (k) => take(keyed.get(k)) ?? take(inner.get(k)) ?? spare?.(k);
  want.forEach((d, i) => {
    if (i < start) return;
    const id = d.attrs["data-mtp-id"];
    let el = id === undefined ? take(loose.get(d.tag)) : find(`${d.tag}#${id}`);
    if (el) patch(el, d, find);
    else el = create(d, find);
    const at = parent.children[i];
    if (at !== el) parent.insertBefore(el, at ?? null);
  });
  while (parent.children.length > want.length) parent.lastElementChild!.remove();
}

// The elements drawing has already given a place this time, which no other place may take.
let placed = new Set<Element>();

function take(pool: Element[] | undefined): Element | undefined {
  while (pool?.length) {
    const el = pool.shift()!;
    if (!placed.has(el)) return el;
  }
  return undefined;
}

// Whether an element's children are already drawn as wanted, as when every shape in a group of
// thousands is kept.
function showing(el: Element, want: Drawn[]): boolean {
  const children = el.children;
  if (children.length !== want.length) return false;
  for (let i = 0; i < want.length; i++) if (DRAWN.get(children[i]!) !== want[i]) return false;
  return true;
}

let made = 0;

/** How many elements drawing has made: none new means each one drawn before is still there. */
export function elementsMade(): number {
  return made;
}

function create(d: Drawn, spare?: Spare): Element {
  made++;
  const el = document.createElementNS(NS, d.tag);
  placed.add(el);
  for (const [k, v] of Object.entries(d.attrs)) setAttr(el, k, v);
  const style = (el as SVGElement).style;
  for (const [k, v] of Object.entries(d.style)) style.setProperty(k, v);
  if (d.text !== null) el.textContent = d.text;
  for (const c of d.children) {
    const id = c.attrs["data-mtp-id"];
    const kept = id === undefined ? undefined : spare?.(`${c.tag}#${id}`);
    if (kept) patch(kept, c);
    el.appendChild(kept ?? create(c, spare));
  }
  DRAWN.set(el, d);
  return el;
}

function patch(el: Element, d: Drawn, spare?: Spare): void {
  placed.add(el);
  const was = DRAWN.get(el)!;
  if (was === d) return;
  for (const k in d.attrs) if (was.attrs[k] !== d.attrs[k]) setAttr(el, k, d.attrs[k]!);
  for (const k in was.attrs) if (!(k in d.attrs)) removeAttr(el, k);
  const style = (el as SVGElement).style;
  for (const k in d.style) if (was.style[k] !== d.style[k]) style.setProperty(k, d.style[k]!);
  for (const k in was.style) if (!(k in d.style)) style.removeProperty(k);
  if (d.text !== was.text) el.textContent = d.text ?? "";
  if ((d.children.length > 0 || was.children.length > 0) && !showing(el, d.children)) patchChildren(el, d.children, spare);
  DRAWN.set(el, d);
}

const XML_NS = "http://www.w3.org/XML/1998/namespace";

function setAttr(el: Element, k: string, v: string): void {
  if (k === "xml:space") el.setAttributeNS(XML_NS, k, v);
  else el.setAttribute(k, v);
}

function removeAttr(el: Element, k: string): void {
  if (k === "xml:space") el.removeAttributeNS(XML_NS, "space");
  else el.removeAttribute(k);
}

// Zoom changes what is sized in screen pixels on the page itself, and what each element was
// last drawn as with it, so the next drawing compares against what the page shows.
function setZoomed(el: Element, attr: string, value: string): void {
  el.setAttribute(attr, value);
  const was = DRAWN.get(el);
  if (was) DRAWN.set(el, { ...was, attrs: { ...was.attrs, [attr]: value } });
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
  // What is inside a fixed-size group is already in pixels: only the group's scale changes.
  const fixed = (el: Element) => el.closest("[data-mtp-fixed-size]") !== null;
  for (const g of svg.querySelectorAll("g[data-mtp-fixed-size]")) {
    setZoomed(g, "transform", matrix(rt.local(Number(g.getAttribute("data-mtp-id")), true, unitsPerPx)));
  }
  for (const el of svg.querySelectorAll("text[data-mtp-id]")) {
    if (fixed(el)) continue;
    setZoomed(el, "font-size", fontSize(rt, Number(el.getAttribute("data-mtp-id")), unitsPerPx));
  }
  for (const m of svg.querySelectorAll("marker[data-mtp-head-px]")) {
    if (fixed(m)) continue;
    const size = String(Number(m.getAttribute("data-mtp-head-px")) * unitsPerPx);
    setZoomed(m, "markerWidth", size);
    setZoomed(m, "markerHeight", size);
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
  else {
    const css = paintCss(rt, root!, "background");
    if (svg.style.getPropertyValue("background-color") !== css) svg.style.setProperty("background-color", css);
  }
}

function drawObject(pass: Pass, i: number, into: Drawn[], unitsPerPx: number, fade = 1): void {
  const rt = pass.rt;
  const o = rt.objects[i]!;
  if (o.kind === "scene") {
    for (const m of o.members ?? []) drawObject(pass, m, into, unitsPerPx, fade);
    return;
  }
  if (o.kind === "group" || o.kind === "instance") {
    if (absent(rt, i)) return;
    const g = node("g", { transform: matrix(rt.local(i, true, unitsPerPx)), "data-mtp-id": i });
    // Inside a fixed-size group one unit is one screen pixel, so what is sized in pixels inside
    // it needs no converting.
    const inside = o["fixed-size"] ? 1 : unitsPerPx;
    if (o["fixed-size"]) g.attrs["data-mtp-fixed-size"] = "";
    if (o.clip !== undefined) clipTo(pass, i, o.clip, g, inside);
    for (const m of o.members ?? []) drawObject(pass, m, g.children, inside, fade);
    into.push(g);
    return;
  }
  const showing = pass.showing;
  if (showing?.governs(i)) {
    if (showing.hidden(i)) return;
    if (showing.standIn(i)) {
      // A stand-in changes with the clock, not with the scene, so it is never kept.
      const drawn = absent(rt, i) ? [] : shapeDrawn(pass, i, unitsPerPx);
      for (const d of drawn) d.attrs["data-mtp-stand-in"] = "";
      into.push(...drawn);
      return;
    }
  } else if (fade < 1) {
    if (fade <= 0) return;
    const g = node("g", { "data-mtp-toggle": "", opacity: fade });
    into.push(g);
    into = g.children;
  }
  const memo = pass.memo && keepable(rt, i) ? pass.memo : null;
  const kept = memo?.shapes.get(i);
  if (kept && rt.touchedAt(i) <= kept.at) {
    into.push(...kept.drawn);
    return;
  }
  const drawn = absent(rt, i) ? [] : shapeDrawn(pass, i, unitsPerPx);
  memo?.shapes.set(i, { at: rt.clock, drawn });
  into.push(...drawn);
}

// Whether what a shape is drawn as follows only its own attributes, so can be kept until one of
// them changes: not in a row or a column, whose places follow the other members, and not a text
// whose font token falls back on another font, which none of its attributes reads.
function keepable(rt: Runtime, i: number): boolean {
  const up = rt.parent(i);
  if (up !== null && rt.objects[up]!.layout) return false;
  if (rt.objects[i]!.kind !== "text") return true;
  const variable = tokenOf(rt, i, "font");
  return variable === null || rt.objects[rt.id(variable)]!.links === undefined;
}

// A shape's heads, then the shape.
function shapeDrawn(pass: Pass, i: number, unitsPerPx: number): Drawn[] {
  const rt = pass.rt;
  const o = rt.objects[i]!;
  const out: Drawn[] = [];
  const el = shapeElement(rt, i, unitsPerPx);
  el.attrs["data-mtp-id"] = String(i);
  const own = rt.local(i);
  if (o.kind === "text") {
    const [x, y] = rt.value(i, "pos") as number[];
    // Text is placed at its anchor and flipped back upright there.
    el.attrs.transform = matrix(compose(FLIP, [1, 0, 0, 1, x!, y!], own));
  } else if (!own.every((v, k) => v === [1, 0, 0, 1, 0, 0][k])) {
    el.attrs.transform = matrix(own);
  }
  paint(rt, i, el);
  const share = o.kind === "text" ? 1 : (rt.value(i, "drawn") as number);
  if (share >= 1) {
    heads(pass, i, el, out, unitsPerPx);
    out.push(el);
    return out;
  }
  const stroked = el.style.stroke !== "none";
  el.style.stroke = "none";
  if (share <= 0 || !stroked) {
    out.push(el);
    return out;
  }
  const line = outlineElement(rt, i, el, share);
  heads(pass, i, line, out, unitsPerPx);
  // The fill and the outline are faded together, as one shape, so the fill does not show
  // through the outline where they overlap.
  const g = node("g", { "data-mtp-drawn": "", opacity: el.attrs.opacity });
  delete el.attrs.opacity;
  delete line.attrs.opacity;
  g.children.push(el, line);
  out.push(g);
  return out;
}

/**
 * The part of a shape's outline drawn so far (mtp-ggsb), as a path of its own in the shape's
 * stroke, with the shape's dashes. It is not the whole outline cut short by a dash pattern with
 * pathLength, since with vector-effect a dash pattern is measured in screen pixels, and since the
 * shape's own dashes must stay. Its heads, markers on it, ride at its ends.
 */
function outlineElement(rt: Runtime, i: number, el: Drawn, share: number): Drawn {
  const kind = rt.objects[i]!.kind;
  const d = outlinePath(drawnPart(outlineOf(kind, (attr) => rt.value(i, attr)), share));
  const line = node("path", { d, "data-mtp-id": i, "data-mtp-outline": "" });
  for (const [k, v] of Object.entries(el.attrs)) {
    if (k.startsWith("stroke") || ["opacity", "transform", "vector-effect", "pointer-events"].includes(k)) line.attrs[k] = v;
  }
  line.style.fill = "none";
  line.style.stroke = paintCss(rt, i, "stroke");
  return line;
}

// A head is this many stroke widths long (mtp-brs), times the shape's head-size.
const HEAD_LENGTH = 5;

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
 * The heads at a line's, a polyline's, a curve's or an arc's ends, as SVG markers in its stroke (mtp-brs).
 * Its stroke width is in screen pixels, which a marker does not follow, so each head is sized in
 * the view's units from its length in pixels, and zoom sizes it again. Several canvases may draw
 * the same shape on one page, so each head's id names its SVG as well as its shape.
 */
function heads(pass: Pass, i: number, el: Drawn, into: Drawn[], unitsPerPx: number): void {
  const rt = pass.rt;
  if (!["line", "polyline", "curve", "arc"].includes(rt.objects[i]!.kind)) return;
  const stroke = paintCss(rt, i, "stroke");
  if (stroke === "none") return;
  const px = HEAD_LENGTH * (rt.value(i, "stroke-width") as number) * (rt.value(i, "head-size") as number);
  for (const end of ["start", "end"] as const) {
    const kind = rt.value(i, `head-${end}`) as string | null;
    const shape = kind === null ? undefined : HEAD_SHAPES[kind];
    if (!shape) continue;
    const id = `mtp-head-${pass.prefix}-${i}-${end}`;
    const marker = node("marker", {
      id,
      viewBox: "0 0 10 10",
      markerUnits: "userSpaceOnUse",
      markerWidth: px * unitsPerPx,
      markerHeight: px * unitsPerPx,
      refX: shape.refX,
      refY: "5",
      // The start's head points back, away from the line, as the end's points forward.
      orient: end === "start" ? "auto-start-reverse" : "auto",
      "data-mtp-head-px": px,
    });
    const mark = node(shape.tag, shape.attrs);
    mark.style.fill = shape.stroked ? "none" : stroke;
    mark.style.stroke = shape.stroked ? stroke : "none";
    if (shape.stroked) {
      // As wide as the line itself: the box is a tenth of the head's length on each side.
      mark.attrs["stroke-width"] = String(10 / HEAD_LENGTH);
      mark.attrs["stroke-linecap"] = "round";
      mark.attrs["stroke-linejoin"] = "round";
    }
    const opacity = String(rt.value(i, "stroke-opacity"));
    mark.attrs[shape.stroked ? "stroke-opacity" : "fill-opacity"] = opacity;
    marker.children.push(mark);
    into.push(marker);
    el.attrs[`marker-${end}`] = `url(#${id})`;
  }
}

// A shape declared T|none is not drawn when it is absent: while its exists-when does not hold, or
// when an attribute it needs is none. Fill, stroke and the heads may be none without it.
const MAY_BE_NONE = new Set(["fill", "stroke", "head-start", "head-end", "exists"]);

// Each kind of object's attributes that must not be none, found once.
const needed = new WeakMap<object, string[]>();

function absent(rt: Runtime, i: number): boolean {
  if (!rt.exists(i)) return true;
  const o = rt.objects[i]!;
  let attrs = needed.get(o);
  if (!attrs) {
    attrs = Object.entries(o.attrs ?? {}).flatMap(([attr, p]) => (!MAY_BE_NONE.has(attr) && p.type ? [attr] : []));
    needed.set(o, attrs);
  }
  return attrs.some((attr) => rt.value(i, attr) === null);
}

/**
 * Clips a container's <g> to its clip shape (mtp-un2f). The clip path sits inside the <g>, in its
 * frame; SVG then also keeps the pointer from what it cuts off. Its id names its SVG and its
 * container, so several canvases may draw the same container on one page.
 */
function clipTo(pass: Pass, container: number, clip: number, g: Drawn, unitsPerPx: number): void {
  const rt = pass.rt;
  const id = `mtp-clip-${pass.prefix}-${container}`;
  const path = node("clipPath", { id });
  const el = shapeElement(rt, clip, unitsPerPx);
  const own = rt.local(clip);
  if (!own.every((v, k) => v === [1, 0, 0, 1, 0, 0][k])) el.attrs.transform = matrix(own);
  path.children.push(el);
  g.children.push(path);
  g.attrs["clip-path"] = `url(#${id})`;
}

// A list of points as SVG writes it. A long one, such as a path through thousands of points, is
// the same list until it is written, so its text is kept with it.
const pointTexts = new WeakMap<object, string>();
function pointsText(points: number[][]): string {
  let s = pointTexts.get(points);
  if (s === undefined) {
    s = points.map((p) => p.join(",")).join(" ");
    pointTexts.set(points, s);
  }
  return s;
}

function shapeElement(rt: Runtime, i: number, unitsPerPx: number): Drawn {
  const v = (attr: string) => rt.value(i, attr) as number;
  const o = rt.objects[i]!;
  switch (o.kind) {
    case "circle":
      return node("circle", { cx: v("x"), cy: v("y"), r: v("r") });
    case "rect":
      // A rect's position is its center.
      return node("rect", {
        x: v("x") - v("width") / 2,
        y: v("y") - v("height") / 2,
        width: v("width"),
        height: v("height"),
        rx: v("rx"),
        ry: v("ry"),
      });
    case "ellipse":
      return node("ellipse", { cx: v("x"), cy: v("y"), rx: v("rx"), ry: v("ry") });
    case "line": {
      const [x1, y1] = rt.value(i, "from") as number[];
      const [x2, y2] = rt.value(i, "to") as number[];
      return node("line", { x1, y1, x2, y2 });
    }
    case "triangle": {
      const corners = ["a", "b", "c"].map((c) => (rt.value(i, c) as number[]).join(","));
      return node("polygon", { points: corners.join(" ") });
    }
    case "polyline":
    case "polygon":
      return node(o.kind, { points: pointsText(rt.value(i, "points") as number[][]) });
    case "curve": {
      const [from, to] = ["from", "to"].map((e) => rt.value(i, e) as number[]);
      return node("path", { d: curvePath(from!, rt.value(i, "controls") as number[][], to!) });
    }
    case "arc":
      return node("path", { d: arcPath(v("x"), v("y"), v("r"), v("from"), v("to")) });
    case "ring":
      return node("path", { d: ringPath(v("x"), v("y"), v("r"), v("width"), v("from"), v("to")) });
    case "text":
      return text(rt, i, unitsPerPx);
    default:
      throw new Error(`cannot draw a ${o.kind}`);
  }
}

function text(rt: Runtime, i: number, unitsPerPx: number): Drawn {
  const el = node("text");
  el.text = String(rt.value(i, "value"));
  // SVG would otherwise drop leading spaces and run spaces together; this keeps each one, and
  // shows a tab or a newline as a space.
  el.attrs["xml:space"] = "preserve";
  const anchor = rt.value(i, "halign");
  if (anchor === "middle" || anchor === "end") el.attrs["text-anchor"] = anchor as string;
  const baseline = { top: "hanging", middle: "central", bottom: "text-after-edge" }[rt.value(i, "valign") as string];
  if (baseline) el.attrs["dominant-baseline"] = baseline;
  const font = rt.value(i, "font") as Record<string, unknown>;
  el.attrs["font-size"] = fontSize(rt, i, unitsPerPx);
  const variable = tokenOf(rt, i, "font");
  for (const part of ["family", "style", "weight"]) {
    const css = variable === null ? font[part] : fontPartCss(rt, rt.id(variable), part);
    if (css !== null && css !== undefined) el.style[`font-${part}`] = String(css);
  }
  return el;
}

// Fill, stroke and their opacities mirror SVG: a color's alpha, fill-opacity and stroke-opacity
// multiply, and opacity fades the drawn shape as a whole.
function paint(rt: Runtime, i: number, el: Drawn): void {
  // A line, a polyline, a curve and an arc are paths with no inside, so their fill is never drawn.
  const open = ["line", "polyline", "curve", "arc"].includes(rt.objects[i]!.kind);
  el.style.fill = open ? "none" : paintCss(rt, i, "fill");
  el.style.stroke = paintCss(rt, i, "stroke");
  const a = el.attrs;
  a["fill-opacity"] = String(rt.value(i, "fill-opacity"));
  a["stroke-opacity"] = String(rt.value(i, "stroke-opacity"));
  a.opacity = String(rt.value(i, "opacity"));
  a["stroke-width"] = String(rt.value(i, "stroke-width"));
  const dash = rt.value(i, "dash") as number[];
  a["stroke-dasharray"] = dash.length ? dash.join(" ") : "none";
  a["stroke-dashoffset"] = String(rt.value(i, "dash-offset"));
  a["stroke-linecap"] = String(rt.value(i, "line-cap"));
  a["stroke-linejoin"] = String(rt.value(i, "line-join"));
  // Stroke widths and dashes are in screen pixels, whatever the view box.
  a["vector-effect"] = "non-scaling-stroke";
  // A group's pointer-events reached its members when compiling, so only shapes carry it.
  if (rt.value(i, "pointer-events") === false) a["pointer-events"] = "none";
}

/** A paint as CSS: none, a color, or one computed from tokens through their CSS variables (docs/mtpc.md). */
export function paintCss(rt: Runtime, i: number, attr: string): string {
  const v = rt.value(i, attr);
  if (v === null) return "none";
  return rt.css(i, attr) ?? String(v);
}

/** A font token's part as CSS: its own variable, falling back to the font it reads the part
 * from, if any, and then to its value. */
function fontPartCss(rt: Runtime, id: number, part: string): string {
  const o = rt.objects[id]!;
  const link = o.links?.[part];
  const own = (rt.value(id, null) as Record<string, unknown>)[part];
  const fallback = link !== undefined ? fontPartCss(rt, link, part) : own === null ? null : String(own);
  return `var(${cssVariable(o.name!)}-${part}${fallback === null ? "" : `, ${fallback}`})`;
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
