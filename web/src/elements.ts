// The page elements (docs/data-model.md, "On the page"): <mtp-model> holds a figure's .mtpc and
// its runtime, and views and controls placed anywhere in the page find it by id, so an author can
// put each one where it fits. Every writer emits writes to the model; views redraw on each change.
import { CONTROLS_CSS } from "./controls-style.ts";
import { placeTicks } from "./ticks.ts";
import { type How, Scheduler } from "./animate.ts";
import { type Transform, apply, equal, invert } from "./builtins.ts";
import { Listeners, heardIn, holds } from "./click.ts";
import { Lifecycle } from "./lifecycle.ts";
import { type Doc, SPEC_VERSION, type Obj, type Type, itemsOf } from "./doc.ts";
import { Drags } from "./drag.ts";
import { latexOf, termClass, typeset } from "./math.ts";
import { Player, type Span } from "./player.ts";
import { Pointer } from "./pointer.ts";
import {
  type Scale,
  chosenIn,
  fractionOf,
  parseNumber,
  pressedThumb,
  snap,
  stepFrom,
  tickValues,
  tidy,
  toggledList,
  valueAt,
} from "./jumpers.ts";
import { Runtime, show } from "./runtime.ts";
import { schemaProblem } from "./schema.ts";
import { Showings } from "./standins.ts";
import { DrawMemo, type Look, draw, elementsMade, fitBox, lookBox, shapesOf, viewOf, zoom } from "./svg.ts";
import { type Ease, applyEase } from "./transitions.ts";

export { SPEC_VERSION };
// The model has loaded (docs/page-interface.md, "Events").
const LOADED = "mtp-loaded";
const CHANGE = "mtp-change";
// An element's page state changed (docs/page-interface.md).
const STATE = "mtp-state";
// Touch (docs/reference.md, "Touch screens"): how far, in CSS pixels, a finger may miss a shape
// and still press it, and how far it may move and still tap.
const TOUCH_REACH = 22;
const TOUCH_SLOP = 8;

/** Whether an element can be seen: neither it nor an ancestor is fully transparent or hidden. */
function shown(el: Element): boolean {
  for (let e: Element | null = el; e; e = e.parentElement) {
    const style = getComputedStyle(e);
    if (style.opacity === "0" || style.visibility === "hidden" || style.display === "none") return false;
  }
  return true;
}

/** How the page asks for animation frames and reads the clock, in milliseconds; tests replace
 * both to move time by hand. */
export const frames = {
  request: (callback: (ms: number) => void): void => {
    requestAnimationFrame(callback);
  },
  now: (): number => performance.now(),
};

export class MtpModel extends HTMLElement {
  runtime: Runtime | null = null;
  scheduler: Scheduler | null = null;
  drags: Drags | null = null;
  clicks: Listeners | null = null;
  releases: Listeners | null = null;
  dragstarts: Listeners | null = null;
  dragends: Listeners | null = null;
  error: string | null = null;
  private running = false;
  private last = 0;

  connectedCallback(): void {
    if (this.runtime || this.error) return;
    const src = this.getAttribute("src");
    if (!src) return;
    if (!src.startsWith("#")) void this.load(src);
    // The block may come later in the page than the element, so it is looked for once the page,
    // or the HTML being added with the element, is all there.
    else if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", () => this.inline(src.slice(1)), { once: true });
    else queueMicrotask(() => this.inline(src.slice(1)));
  }

  /** Reads the compiled model from the JSON script with the given id, which may be anywhere in the
   * page: Markdown converters keep such a block intact only where it stands on its own. */
  private inline(id: string): void {
    if (this.runtime || this.error) return;
    const block = document.getElementById(id);
    if (!(block instanceof HTMLScriptElement)) {
      this.fail(`the page has no script with the id ${id} to read the compiled model from`);
      return;
    }
    try {
      this.doc = JSON.parse(block.textContent ?? "") as Doc;
    } catch (err) {
      this.fail(`could not read the compiled model in #${id}: ${(err as Error).message}`);
    }
  }

  private async load(src: string): Promise<void> {
    try {
      const response = await fetch(src);
      if (!response.ok) throw new Error(`could not load ${src}: ${response.status}`);
      this.doc = (await response.json()) as Doc;
    } catch (err) {
      this.fail((err as Error).message);
    }
  }

  set doc(doc: Doc) {
    if (doc.mtpc !== SPEC_VERSION) {
      this.fail(`this runtime reads .mtpc files of spec version ${SPEC_VERSION}, but this file states version ${String(doc.mtpc)}`);
      return;
    }
    const problem = schemaProblem(doc);
    if (problem) {
      this.fail(problem);
      return;
    }
    const rt = new Runtime(doc);
    this.runtime = rt;
    const scheduler = new Scheduler(
      () => this.changed(),
      () => this.wake(),
      (target) => {
        const at = target.indexOf(":");
        return rt.slotsOf(Number(target.slice(0, at)), target.slice(at + 1) || null);
      },
    );
    this.scheduler = scheduler;
    // Every write a writer makes is decided, free value by free value (docs/concurrency-model.md).
    rt.gate = (k) => scheduler.accept(k);
    this.drags = new Drags(rt);
    this.clicks = new Listeners(rt, "on-click");
    this.releases = new Listeners(rt, "on-release");
    this.dragstarts = new Listeners(rt, "on-dragstart");
    this.dragends = new Listeners(rt, "on-dragend");
    this.error = null;
    // Made before the page hears of any change, so it reads the values at page load.
    lives.set(
      this,
      new Lifecycle(
        rt,
        scheduler,
        (o) => playerFor(rt, o),
        (i) => activeOf(rt, i),
        () => this.changed(),
      ),
    );
    rt.onChange(() => this.changed());
    this.dispatchEvent(new Event(LOADED, { bubbles: true }));
    // The views of the page are there once it is told the model is ready, or, for those added
    // with it, once the HTML being added is all there.
    checkPageReady(this);
    // Once every element of the page is built, the controls show whether the canvases they
    // belong to are ready.
    queueMicrotask(() => this.changed());
  }

  /** Tells every view and control of this model to show the current values. */
  changed(): void {
    this.scheduler?.told();
    this.dispatchEvent(new Event(CHANGE, { bubbles: true }));
    checkPageReady(this);
  }

  private wake(): void {
    if (this.running) return;
    this.running = true;
    this.last = performance.now();
    frames.request((ms) => this.frame(ms));
  }

  private frame(ms: number): void {
    const scheduler = this.scheduler;
    if (!scheduler) return;
    scheduler.tick(Math.max(ms - this.last, 0) / 1000);
    this.last = ms;
    if (scheduler.busy()) frames.request((next) => this.frame(next));
    else this.running = false;
  }

  private fail(message: string): void {
    this.runtime = null;
    this.scheduler = null;
    this.error = message;
    this.dispatchEvent(new Event(LOADED, { bubbles: true }));
  }
}

// Each model's canvases' lifecycles, kept off the element: no element has methods that change it.
const lives = new WeakMap<MtpModel, Lifecycle>();

/** Puts data-mtp-ready on the model once every canvas, display and readout copy of it on the page
 * is ready, and fires mtp-state when that changes (docs/canvas-lifecycle.md, rule 8). */
function checkPageReady(model: MtpModel): void {
  if (!model.runtime || !model.id) return;
  const views = document.querySelectorAll(`:is(mtp-canvas, mtp-display, mtp-readout)[model="${CSS.escape(model.id)}"]`);
  const ready = [...views].every((v) => v.hasAttribute("data-mtp-ready"));
  if (model.hasAttribute("data-mtp-ready") === ready) return;
  model.toggleAttribute("data-mtp-ready", ready);
  model.dispatchEvent(new Event(STATE, { bubbles: true }));
}

// What marks each view copy seen, as its watch does once it first comes into view.
const seers = new WeakMap<Element, () => void>();

/** Marks a view copy as having come into view, as the page does the first time it does: tests
 * and recording use it where nothing scrolls. */
export function markSeen(copy: Element): void {
  seers.get(copy)?.();
}

/** Makes a view with a quiet mode live, or quiet again (docs/reference.md, "Quiet and live
 * views"), playing its active on-live or on-quiet listeners. A function, not a method of the
 * model: no element has methods that change it (docs/page-interface.md). */
function setLive(model: MtpModel, view: number, live: boolean): void {
  const rt = model.runtime;
  const scheduler = model.scheduler;
  if (!rt || !scheduler || !rt.quietMode.has(view) || rt.quiet.has(view) !== live) return;
  if (live) rt.quiet.delete(view);
  else rt.quiet.add(view);
  const kind = live ? "on-live" : "on-quiet";
  rt.objects.forEach((o, i) => {
    if (o.kind !== kind || o.view !== view || !activeOf(rt, i)) return;
    const player = playerFor(rt, o);
    if (player) scheduler.start(player, o, howOf(o, true));
  });
  model.changed();
}

// What views and controls share: finding their model and their object, and hearing when the
// model loads or changes.
abstract class MtpPart extends HTMLElement {
  private onReady = (event: Event) => {
    if (this.mine(event)) this.build();
  };
  private onChange = (event: Event) => {
    if (!this.mine(event)) return;
    this.guard(() => this.update());
    this.moded(false);
    this.lifecycle();
  };

  connectedCallback(): void {
    document.addEventListener(LOADED, this.onReady);
    document.addEventListener(CHANGE, this.onChange);
    this.addEventListener("keydown", this.onKey);
    const model = this.model();
    if (model && (model.runtime || model.error)) this.build();
  }

  disconnectedCallback(): void {
    document.removeEventListener(LOADED, this.onReady);
    document.removeEventListener(CHANGE, this.onChange);
    this.removeEventListener("keydown", this.onKey);
  }

  private mine(event: Event): boolean {
    return (event.target as Element).id === this.getAttribute("model");
  }

  protected model(): MtpModel | null {
    const id = this.getAttribute("model");
    const el = id ? document.getElementById(id) : null;
    return el instanceof MtpModel ? el : null;
  }

  private build(): void {
    this.guard(() => {
      const model = this.model();
      if (model?.error) throw new Error(model.error);
      if (model?.runtime && model.scheduler) {
        this.switch = null;
        this.folded = null;
        this.setup(model, model.runtime, model.scheduler);
        this.moded(true);
        this.seenOnce = false;
        this.readyOnce = false;
        this.watch(model);
        this.lifecycle();
        checkPageReady(model);
      }
    });
  }

  // Whether this view copy has come into view, and has been ready, yet.
  private seenOnce = false;
  private readyOnce = false;

  // A view copy's lifecycle (docs/canvas-lifecycle.md): from the moment its canvas is ready it
  // has data-mtp-ready, and its switch takes input.
  private lifecycle(): void {
    const model = this.model();
    const id = this.shown;
    const life = model ? lives.get(model) : undefined;
    if (!model || !life || id === null || this.readyOnce || !VIEWS.has(model.runtime!.objects[id]!.kind)) return;
    life.check(id);
    if (this.switch) this.switch.disabled = !life.ready(id);
    if (!life.ready(id)) return;
    this.readyOnce = true;
    this.pageState({ ready: true });
  }

  // Tells the lifecycle when this view copy first comes into view (on-view). On screen is not
  // enough: a page may hide its content at opacity 0 while it loads, so the element counts as in
  // view only once no ancestor is fully transparent or hidden, checked again each frame meanwhile.
  private watch(model: MtpModel): void {
    const id = this.shown;
    if (id === null || !VIEWS.has(model.runtime!.objects[id]!.kind)) return;
    seers.set(this, () => {
      if (this.seenOnce) return;
      this.seenOnce = true;
      this.pageState({ seen: true });
      lives.get(model)?.seen(this, id);
      this.lifecycle();
      checkPageReady(model);
    });
    if (typeof IntersectionObserver === "undefined") return;
    let onScreen = false;
    let checking = false;
    const check = () => {
      checking = false;
      if (!onScreen) return;
      if (!shown(this)) {
        checking = true;
        frames.request(check);
        return;
      }
      observer.disconnect();
      markSeen(this);
    };
    const observer = new IntersectionObserver((entries) => {
      onScreen = entries.some((e) => e.isIntersecting);
      if (onScreen && !checking) check();
    });
    observer.observe(this);
  }

  private guard(work: () => void): void {
    try {
      work();
    } catch (err) {
      const message = document.createElement("pre");
      message.className = "mtp-error";
      message.textContent = (err as Error).message;
      this.replaceChildren(message);
    }
  }

  // The object this element shows, once found.
  private shown: number | null = null;
  // A view's button to make it live and back to quiet, when it has a quiet mode.
  private switch: HTMLButtonElement | null = null;
  private switchQuiet: boolean | null = null;
  private folding: Animation | null = null;
  private folded: boolean | null = null;
  private onKey = (event: KeyboardEvent) => {
    const rt = this.model()?.runtime;
    const id = this.shown;
    if (event.key === "Escape" && rt && id !== null && rt.quietMode.has(id) && !rt.quiet.has(id)) setLive(this.model()!, id, false);
  };

  /**
   * Shows the element's page state as data-mtp-… attributes, present or absent for true or false
   * and a value otherwise, and fires mtp-state when any of them changes (docs/page-interface.md).
   */
  protected pageState(state: Record<string, string | boolean>): void {
    let changed = false;
    for (const [name, v] of Object.entries(state)) {
      const attr = `data-mtp-${name}`;
      const now = v === false ? null : v === true ? "" : v;
      if (this.getAttribute(attr) === now) continue;
      if (now === null) this.removeAttribute(attr);
      else this.setAttribute(attr, now);
      changed = true;
    }
    if (changed) this.dispatchEvent(new Event(STATE, { bubbles: true }));
  }

  /** Puts nodes in the element, with the view's switch after them. */
  protected present(...nodes: Node[]): void {
    this.replaceChildren(...nodes);
    if (this.switch) this.append(this.switch);
  }

  /** Follows whether a view is quiet or live: a view with a quiet mode shows it and its switch,
   * and a control tied to views is folded away while every one of them is quiet. The first
   * time, at setup, nothing is animated. */
  private moded(first: boolean): void {
    const model = this.model();
    const rt = model?.runtime;
    const id = this.shown;
    if (!model || !rt || id === null) return;
    const obj = rt.objects[id]!;
    if (VIEWS.has(obj.kind)) {
      if (!rt.quietMode.has(id)) return;
      const quiet = rt.quiet.has(id);
      this.pageState({ mode: quiet ? "quiet" : "live" });
      if (!this.switch) {
        this.switch = makeSwitch(this, () => setLive(model, id, rt.quiet.has(id)));
        this.append(this.switch);
      } else if (!first && this.switchQuiet === quiet) return;
      this.switchQuiet = quiet;
      this.switch.innerHTML = quiet ? HAND_ICON : CLOSE_ICON;
      const label = quiet ? "Interactive figure: open it" : "Back to the plain figure";
      this.switch.setAttribute("aria-label", label);
      this.switch.title = label;
      return;
    }
    if (!obj.in) return;
    this.fold(obj.in.every((v) => rt.quiet.has(v)), !first);
  }

  // A control unfolds by growing to its height and fading in, and folds the other way.
  // data-mtp-folded is where it is going, at once; while data-mtp-folding is there too, it is
  // still drawn, on its way.
  private fold(folded: boolean, animate: boolean): void {
    if (this.folded === folded) return;
    this.folded = folded;
    this.folding?.cancel();
    this.folding = null;
    this.removeAttribute("data-mtp-folding");
    const still = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!animate || still || typeof this.animate !== "function") {
      this.toggleAttribute("data-mtp-folded", folded);
      return;
    }
    this.removeAttribute("data-mtp-folded");
    const open = { height: `${this.getBoundingClientRect().height}px`, opacity: 1 };
    const shut = { height: "0px", opacity: 0 };
    this.setAttribute("data-mtp-folding", "");
    this.toggleAttribute("data-mtp-folded", folded);
    const animation = this.animate(folded ? [open, shut] : [shut, open], { duration: FOLD_MS, easing: "ease" });
    this.folding = animation;
    // A fold cancelled by the next one ends here too, rejected, which is no error.
    animation.finished.then(
      () => {
        if (this.folding !== animation) return;
        this.folding = null;
        this.removeAttribute("data-mtp-folding");
      },
      () => {},
    );
  }

  /** The id of the object this element shows, by its name attribute and kind. */
  protected find(rt: Runtime, kind: string): number {
    const name = this.getAttribute("name");
    const id = name === null ? undefined : rt.doc.names[name];
    const obj = id === undefined ? undefined : rt.objects[id];
    if (!obj) throw new Error(`no ${kind} named ${String(name)}`);
    if (obj.kind !== kind) throw new Error(`${String(name)} is a ${obj.kind}, not a ${kind}`);
    this.shown = id!;
    return id!;
  }

  protected abstract setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void;
  protected abstract update(): void;
}

// The views (docs/data-model.md, "Components"): what may have a quiet mode.
const VIEWS = new Set(["canvas", "readout", "display"]);
// How long a control takes to unfold when its view goes live, in milliseconds.
const FOLD_MS = 300;
// The switch's icons (Tabler's hand-finger and x): a hand, to make a view live, as in the Bourgain
// paper's figures, and a cross to put it back to quiet. Tabler draws both as outlines.
const HAND_ICON =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 13v-8.5a1.5 1.5 0 0 1 3 0v7.5"/><path d="M11 11.5v-2a1.5 1.5 0 1 1 3 0v2.5"/><path d="M14 10.5a1.5 1.5 0 0 1 3 0v1.5"/><path d="M17 11.5a1.5 1.5 0 0 1 3 0v4.5a6 6 0 0 1 -6 6h-2h.208a6 6 0 0 1 -5.012 -2.7a69.74 69.74 0 0 1 -.196 -.3c-.312 -.479 -1.407 -2.388 -3.286 -5.728a1.5 1.5 0 0 1 .536 -2.022a1.867 1.867 0 0 1 2.28 .28l1.47 1.47"/></svg>';
const CLOSE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6l-12 12"/><path d="M6 6l12 12"/></svg>';

/** A view's switch: one button that makes it live and, pressed again, quiet, so the keyboard's
 * focus stays on it. A readout and a formula inside a paragraph take it in the line. */
function makeSwitch(view: HTMLElement, press: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "mtp-switch";
  button.dataset.mtpInput = "switch";
  if (view.localName === "mtp-readout" || view.style.display === "inline") button.classList.add("mtp-switch-inline");
  button.addEventListener("click", press);
  return button;
}

/** How a writer was set off, by the reader or not (on-view), and the priority it gives, if any
 * (docs/concurrency-model.md). */
function howOf(writer: Obj, reader: boolean): How {
  return { reader, priority: writer.priority };
}

function playerFor(rt: Runtime, writer: Obj): Player | null {
  return writer.animation === null || writer.animation === undefined
    ? null
    : new Player(rt, writer.animation, writer.conditions ?? [], writer.rest ?? 0);
}

export class MtpCanvas extends MtpPart {
  private redraw: () => void = () => {};
  private showings: Showings | null = null;

  /** A shape's attribute as this canvas draws it now, its stand-in's while its on-show or
   * on-hide plays, or null while it does not draw the shape (mtp-7i3j). */
  drawnAs(shape: number, attr: string): unknown {
    return this.showings?.drawnAs(shape, attr) ?? null;
  }

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const canvas = this.find(rt, "canvas");
    let here = placed.get(rt);
    if (!here) placed.set(rt, (here = new Set()));
    here.add(canvas);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    const drags = model.drags!;
    const clicks = model.clicks!;
    const releases = model.releases!;
    const dragstarts = model.dragstarts!;
    const dragends = model.dragends!;
    const showings = new Showings(rt, canvas, scheduler, () => this.redraw());
    this.showings = showings;
    const toggles = new Toggles(rt, canvas, scheduler, () => this.redraw(), showings);
    const look: Look = { scale: 1, dx: 0, dy: 0 };
    const pointer = new Pointer(rt, canvas);
    // The shape a tap selected, to move by the next tap, as the drag from the press point there.
    let selection: { hit: number; shape: number; at: [number, number] } | null = null;
    // Whether the finger just pressed is on a shape it can act on. Chromium does not heed
    // touch-action on the shapes inside an SVG, so the page is kept from scrolling by the
    // touchstart that follows the pointerdown. That goes to the element pressed, which the
    // pointerdown's drawing may have taken off the page, so the element pressed listens, as well
    // as the canvas.
    let held = false;
    const hold = (event: Event) => {
      if (held) event.preventDefault();
    };
    const reaches = (id: number) =>
      drags.draggable(id, canvas) || clicks.find(id, canvas).length > 0 || releases.find(id, canvas).length > 0 || pointer.hears(id);
    const mark = () => {
      const want = selection ? `${selection.shape}` : null;
      for (const el of svg.querySelectorAll(".mtp-selected")) {
        if (el.getAttribute("data-mtp-id") !== want) el.classList.remove("mtp-selected");
      }
      if (want !== null) for (const el of svg.querySelectorAll(`[data-mtp-id="${want}"]`)) el.classList.add("mtp-selected");
    };
    const memo = new DrawMemo();
    // The model's clock and the elements made when the pointers and the selection were last
    // shown: drawing keeps the elements of shapes still drawn, so they need showing again only
    // after a write, which may change what can be dragged or clicked, or on new elements.
    let shownAt = -1;
    let madeAt = -1;
    // A quiet canvas neither pans nor zooms, so a reader scrolling past on a phone is not caught
    // by it (the author, 2026-11-08).
    const allows = (attr: "pan" | "zoom") => !rt.quiet.has(canvas) && Boolean(rt.value(canvas, attr));
    let wasQuiet = rt.quiet.has(canvas);
    // A canvas with no view box of its own shows the box of its shapes as this copy first draws
    // them, and keeps it (the author, 2026-11-16). A text's size in the scene follows the copy's
    // width on screen, so the box is worked out again once, the first time the copy has a width:
    // until then the page shows nothing of it.
    const fits = Boolean(rt.objects[canvas]!.fit);
    let fitted: number[] | undefined;
    let sized = false;
    const view = () => viewOf(rt, canvas, fitted);
    this.redraw = () => {
      toggles.follow();
      const quiet = rt.quiet.has(canvas);
      // Back to quiet, the reader can no longer undo a pan or zoom, so the canvas drops it.
      if (quiet && !wasQuiet) Object.assign(look, { scale: 1, dx: 0, dy: 0 });
      // Going live or back changes what its listeners hear, so what can be dragged or clicked.
      const moded = quiet !== wasQuiet;
      wasQuiet = quiet;
      // Elsewhere a finger on the canvas scrolls the page.
      const action = allows("pan") || allows("zoom") || pointer.onCanvas ? "none" : "";
      if (svg.style.touchAction !== action) svg.style.touchAction = action;
      const shownBy = (k: number) => toggles.shownBy(k);
      if (fits && !sized) {
        fitted ??= fitBox(rt, canvas);
        const width = svg.getBoundingClientRect?.().width ?? 0;
        if (width > 0) {
          // Drawn first with each text at its position, so that the texts are on the page to
          // measure.
          draw(rt, canvas, svg, shownBy, look, memo, showings, fitted);
          fitted = fitBox(rt, canvas, svg, width, fitted);
          sized = true;
        }
      }
      draw(rt, canvas, svg, shownBy, look, memo, showings, fitted);
      const made = elementsMade();
      if (rt.clock !== shownAt || made !== madeAt || moded) {
        for (const el of svg.querySelectorAll<SVGElement>("[data-mtp-id]")) {
          const id = Number(el.getAttribute("data-mtp-id"));
          const cursor = drags.draggable(id, canvas) || clicks.find(id, canvas).length ? "pointer" : "";
          if (el.style.cursor !== cursor) el.style.cursor = cursor;
        }
      }
      if (made !== madeAt) mark();
      [shownAt, madeAt] = [rt.clock, made];
    };
    this.present(svg);
    this.redraw();
    // Font sizes are in screen pixels, so the drawing depends on the canvas's size on screen.
    let width = 0;
    new ResizeObserver(() => {
      forget();
      const now = svg.getBoundingClientRect().width;
      memo.width = now;
      if (now !== width) {
        width = now;
        this.redraw();
      }
    }).observe(svg);
    // The shape under the pointer. While the canvas holds the pointer, to pan or drag, every
    // event's target is the SVG itself, so the shape is found from where the pointer is.
    const hitOf = (event: PointerEvent): number | null => {
      let at = event.target as Element | null;
      if (at === svg) at = document.elementFromPoint?.(event.clientX, event.clientY) ?? at;
      const under = at?.closest?.("[data-mtp-id]");
      return under && svg.contains(under) ? Number(under.getAttribute("data-mtp-id")) : null;
    };
    // A finger is wide and hides what it presses, so a shape it can act on takes it within
    // TOUCH_REACH pixels of what is drawn: a target at least 44 pixels across. The nearest wins.
    const nearest = (x: number, y: number): number | null => {
      let best: number | null = null;
      let gap = TOUCH_REACH;
      for (const el of svg.querySelectorAll("[data-mtp-id]")) {
        if (el.querySelector("[data-mtp-id]") || el.closest('[pointer-events="none"]')) continue;
        if (!reaches(Number(el.getAttribute("data-mtp-id")))) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        const d = Math.hypot(Math.max(r.left - x, 0, x - r.right), Math.max(r.top - y, 0, y - r.bottom));
        if (d <= gap) [best, gap] = [Number(el.getAttribute("data-mtp-id")), d];
      }
      return best;
    };
    // A pen that hovers is a mouse; one that does not, a finger.
    let penHovers = false;
    const touchy = (event: PointerEvent) => event.pointerType === "touch" || (event.pointerType === "pen" && !penHovers);
    const targetOf = (event: PointerEvent): number | null => {
      const hit = hitOf(event);
      if (!touchy(event) || (hit !== null && reaches(hit))) return hit;
      return nearest(event.clientX, event.clientY) ?? hit;
    };
    // The pointer in the SVG's own coordinates, and in scene coordinates through the canvas's view.
    let screen: Screen | null = null;
    const measure = () => {
      screen = screenOf(svg);
    };
    const forget = () => {
      screen = null;
    };
    window.addEventListener("resize", forget, { passive: true });
    document.addEventListener("scroll", forget, { passive: true, capture: true });
    svg.addEventListener("pointerenter", measure);
    const toUser = (event: { clientX: number; clientY: number }): [number, number] => {
      const at: [number, number] = [event.clientX, event.clientY];
      const box = svg.viewBox?.baseVal;
      if (!box || !box.width || !box.height) return at;
      if (!screen || screen.aspect !== box.width / box.height) screen = screenOf(svg);
      if (!screen) return at;
      const [u, v] = apply(screen.back, at) as [number, number];
      return [box.x + u * box.width, box.y + v * box.height];
    };
    const toScene = (event: PointerEvent): [number, number] =>
      apply(invert(view().toUser), toUser(event)) as [number, number];
    // The reader zooms between the canvas's bounds. Zoomed in, what is shown stays inside the
    // view box, so the reader never sees past what the author framed (the author, 2026-11-04);
    // zoomed out past it, the view box stays inside what is shown (the author, 2026-11-08).
    const inside = () => {
      const [, , w, h] = view().box as [number, number, number, number];
      const [mx, my] = [Math.abs(w - w / look.scale) / 2, Math.abs(h - h / look.scale) / 2];
      look.dx = Math.min(Math.max(look.dx, -mx), mx);
      look.dy = Math.min(Math.max(look.dy, -my), my);
    };
    const zoomAbout = (at: [number, number], by: number) => {
      const [x, y, w, h] = view().box as [number, number, number, number];
      const [cx, cy] = [x + w / 2, y + h / 2];
      const [lo, hi] = [rt.value(canvas, "zoom-min") as number, rt.value(canvas, "zoom-max") as number];
      const factor = Math.min(Math.max(look.scale * by, lo), hi) / look.scale;
      // The point under the pointer stays where it is.
      look.dx = at[0] + (cx + look.dx - at[0]) / factor - cx;
      look.dy = at[1] + (cy + look.dy - at[1]) / factor - cy;
      look.scale *= factor;
      inside();
      zoom(rt, canvas, svg, look, fitted);
    };
    // The wheel zooms, and so does a pinch on a trackpad, which comes as a wheel with ctrl held.
    svg.addEventListener("wheel", (event) => {
      if (!allows("zoom")) return;
      event.preventDefault();
      zoomAbout(toUser(event), Math.exp(-event.deltaY * 0.002));
    });
    svg.addEventListener("dblclick", () => {
      if (!allows("pan") && !allows("zoom")) return;
      Object.assign(look, { scale: 1, dx: 0, dy: 0 });
      zoom(rt, canvas, svg, look, fitted);
    });
    // The pointers pressed where nothing is dragged, and where each is: one pans, two pinch.
    const touches = new Map<number, [number, number]>();
    const unitsPerPx = () =>
      lookBox(view().box, look)[2]! / (svg.getBoundingClientRect?.().width || 640);
    const spread = () => {
      const [a, b] = [...touches.values()] as [[number, number], [number, number]];
      return { gap: Math.hypot(a[0] - b[0], a[1] - b[1]), mid: { clientX: (a[0] + b[0]) / 2, clientY: (a[1] + b[1]) / 2 } };
    };
    // The shape pressed, for the click on release; drawing replaces the elements, so shapes are
    // compared by id.
    let pressed: number | null = null;
    // Where a finger came down, to tell a tap from a drag: a finger is never quite still.
    let press: { id: number; x: number; y: number; at: [number, number]; moved: boolean } | null = null;
    // A drag the reader holds is a held writer from its first move to the release: a grab that
    // moves nothing writes nothing. One cancelled while held stops writing.
    let gripped = false;
    const grip = () => scheduler.grip(drags, howOf(drags.listener!, true), () => drags.cancel());
    const dragTo = (at: [number, number]) => scheduler.instant(drags, { ...howOf(drags.listener!, true), held: true }, () => drags.move(at));
    const play = (listeners: (Obj | null)[]) => {
      for (const listener of listeners) {
        const player = listener ? playerFor(rt, listener) : null;
        if (listener && player) scheduler.start(player, listener, howOf(listener, true));
      }
    };
    // on-enter, on-leave and on-pointermove. A finger has no hover, so a tap enters a shape and
    // it stays entered until the reader presses elsewhere, here or anywhere on the page.
    const follow = (event: PointerEvent, hit: number | null) => {
      play(pointer.onto(hit));
      pointer.move(toScene(event), (_targets, l, write) => scheduler.instant(l, { ...howOf(l, true), held: true }, write));
    };
    const deselect = () => {
      if (selection === null) return;
      selection = null;
      mark();
    };
    document.addEventListener(
      "pointerdown",
      (event) => {
        if (!svg.isConnected || !touchy(event) || svg.contains(event.target as Node)) return;
        play(pointer.onto(null));
        deselect();
      },
      true,
    );
    svg.addEventListener("touchstart", hold, { passive: false });
    svg.addEventListener("pointerleave", (event) => {
      if (!touchy(event)) play(pointer.onto(null));
    });
    svg.addEventListener("pointerdown", (event) => {
      measure();
      const touch = touchy(event);
      pressed = touch ? targetOf(event) : hitOf(event);
      held = touch && pressed !== null && reaches(pressed);
      if (held && event.target !== svg) (event.target as Element).addEventListener("touchstart", hold, { passive: false, once: true });
      follow(event, pressed);
      if (touch && event.isPrimary) {
        press = { id: event.pointerId, x: event.clientX, y: event.clientY, at: toScene(event), moved: false };
      }
      if (pressed !== null && drags.grab(pressed, toScene(event), canvas)) {
        // The drag is a running writer of its targets from its first move to the release
        // (mtp-vs5d): a grab that changes nothing writes nothing (the author, 2026-11-12).
        gripped = false;
      } else if (allows("pan") || allows("zoom")) {
        touches.set(event.pointerId, [event.clientX, event.clientY]);
      } else {
        // A finger's events go to the element it pressed, which drawing may replace, and then
        // they reach nothing: the canvas holds them instead.
        if (touch) svg.setPointerCapture?.(event.pointerId);
        return;
      }
      event.preventDefault();
      svg.setPointerCapture?.(event.pointerId);
    });
    svg.addEventListener("pointermove", (event) => {
      if (event.pointerType === "pen" && event.buttons === 0) penHovers = true;
      // A finger that has not yet moved from its press stays on what it pressed. Once it moves, it
      // is on what is under it: finding the nearest shape at every move would cost a layout each.
      if (press && press.id === event.pointerId && !press.moved) {
        if (Math.hypot(event.clientX - press.x, event.clientY - press.y) < TOUCH_SLOP) {
          follow(event, pressed);
          return;
        }
        press.moved = true;
      }
      follow(event, hitOf(event));
      if (drags.dragging) {
        if (!gripped) {
          gripped = true;
          grip();
        }
        // As JS's dragstart, a drag starts at its first move, and its listeners play before the
        // drag writes, so they may reset what the drag then reads (mtp-5opl).
        if (!drags.moved) play(dragstarts.find(drags.shape!, canvas));
        dragTo(toScene(event));
        return;
      }
      const was = touches.get(event.pointerId);
      if (!was) return;
      if (touches.size === 1) {
        if (!allows("pan")) return;
        touches.set(event.pointerId, [event.clientX, event.clientY]);
        const upp = unitsPerPx();
        look.dx -= (event.clientX - was[0]) * upp;
        look.dy -= (event.clientY - was[1]) * upp;
        inside();
        // A pan keeps the scale, so the shapes, whose text sizes follow the scale, stay as
        // drawn: only the view box moves.
        svg.setAttribute("viewBox", lookBox(view().box, look).join(" "));
      } else if (touches.size === 2) {
        const before = spread();
        touches.set(event.pointerId, [event.clientX, event.clientY]);
        const after = spread();
        if (allows("zoom") && before.gap > 0) zoomAbout(toUser(after.mid), after.gap / before.gap);
      }
    });
    const lift = (event: PointerEvent) => touches.delete(event.pointerId);
    // The tap alternative to a drag (WCAG 2.2, 2.5.7): a tap on a draggable shape selects it, and
    // the next tap on the canvas drags it from the press point to there; a tap on it again ends
    // the selection, and so does any press that is not a tap. Gives the shape moved, if any.
    const tapped = (event: PointerEvent, grabbed: number | null): number | null => {
      const tap = press !== null && press.id === event.pointerId && !press.moved;
      const chosen = selection;
      if (tap && chosen === null && grabbed !== null) {
        selection = { hit: pressed!, shape: grabbed, at: press!.at };
        mark();
        return null;
      }
      deselect();
      if (!tap || chosen === null || grabbed === chosen.shape || !drags.grab(chosen.hit, chosen.at, canvas)) return null;
      grip();
      play(dragstarts.find(drags.shape!, canvas));
      dragTo(toScene(event));
      drags.release();
      scheduler.letGo(drags);
      return chosen.shape;
    };
    svg.addEventListener("pointerup", (event) => {
      lift(event);
      const touch = touchy(event);
      // As JS's dragend, only a drag that moved ends.
      const ended = drags.moved ? drags.shape : null;
      const grabbed = drags.shape;
      drags.release();
      scheduler.letGo(drags);
      const moved = touch ? tapped(event, grabbed) : null;
      const released = touch && press?.id === event.pointerId && !press.moved ? pressed : hitOf(event);
      // pointerup comes before click, as in JS; the end of a drag comes between them.
      // As JS's click: on the nearest shape holding both the pressed and the released one,
      // whatever the pointer did between.
      const both = pressed !== null && released !== null ? holding(rt, pressed, released) : null;
      play([
        ...(released !== null ? releases.find(released, canvas) : []),
        ...(ended !== null ? dragends.find(ended, canvas) : []),
        ...(moved !== null ? dragends.find(moved, canvas) : []),
        ...(both !== null ? clicks.find(both, canvas) : []),
      ]);
      pressed = null;
      if (press?.id === event.pointerId) press = null;
    });
    svg.addEventListener("pointercancel", (event) => {
      lift(event);
      drags.release();
      scheduler.letGo(drags);
      if (!touchy(event)) {
        play(pointer.onto(null));
        return;
      }
      // The page took the finger, to scroll: what it entered stays entered.
      if (press?.id === event.pointerId) {
        press = null;
        deselect();
      }
      pressed = null;
    });
  }

  protected update(): void {
    this.redraw();
  }
}

// How visible each shape a canvas item gives is: the canvas's own state. When an item starts or
// stops giving a shape, a toggle moves that shape's level over the canvas's toggle-duration with
// its toggle-ease. Turning back midway covers only what is left, at the same speed. A shape with
// an on-show or on-hide is not faded so: its listeners show and hide it (mtp-7i3j), and a shape
// an item no longer gives is kept while one of its stand-ins still hides.
class Toggles {
  // Each item's shapes, by "k:id", and how far each is shown, from 0 to 1.
  private levels = new Map<string, number>();
  private wanted = new Set<string>();
  // Each item's shapes in the order to draw them: those it gives now, then those leaving.
  private order: number[][] = [];
  private moving = false;
  private duration: number;
  private ease: Ease;

  constructor(
    private rt: Runtime,
    private canvas: number,
    private scheduler: Scheduler,
    private redraw: () => void,
    private showings: Showings,
  ) {
    const view = rt.objects[canvas]!;
    const tr = view.transition === null || view.transition === undefined ? null : rt.objects[view.transition]!;
    this.duration = tr?.duration ?? 0;
    this.ease = (tr?.ease as Ease | null) ?? "linear";
    this.order = this.now();
    this.wanted = this.keys(this.order);
    for (const key of this.wanted) this.levels.set(key, 1);
  }

  private now(): number[][] {
    return itemsOf(this.rt.objects[this.canvas]!).map((item) => shapesOf(this.rt.evaluate(item)));
  }

  private keys(order: number[][]): Set<string> {
    return new Set(order.flatMap((ids, k) => ids.map((id) => `${k}:${id}`)));
  }

  /** Starts moving each shape toward whether its item gives it now. */
  follow(): void {
    const now = this.now();
    const wanted = this.keys(now);
    if (this.showings.any) {
      const bare = (this.rt.objects[this.canvas]!.shows ?? []).filter((s): s is number => typeof s === "number");
      this.showings.follow(new Set([...bare, ...now.flat()]));
    }
    const held = (key: string) => this.showings.holds(Number(key.slice(key.indexOf(":") + 1)));
    for (const [key, level] of this.levels) if (level <= 0 && !wanted.has(key) && !held(key)) this.levels.delete(key);
    const same = wanted.size === this.wanted.size && [...wanted].every((key) => this.wanted.has(key));
    // Leaving shapes keep their place after the ones the item gives now, until they are gone.
    this.order = now.map((ids, k) => [...ids, ...(this.order[k] ?? []).filter((id) => !ids.includes(id))]);
    if (same) return;
    this.wanted = wanted;
    for (const key of wanted) if (!this.levels.has(key)) this.levels.set(key, 0);
    if (this.duration <= 0) {
      for (const key of [...this.levels.keys()]) {
        if (wanted.has(key)) this.levels.set(key, 1);
        else if (held(key)) this.levels.set(key, 0);
        else this.levels.delete(key);
      }
      return;
    }
    if (this.moving) return;
    this.moving = true;
    this.scheduler.addTicker((seconds) => {
      const step = seconds / this.duration;
      this.moving = false;
      for (const [key, level] of this.levels) {
        const next = this.wanted.has(key) ? Math.min(level + step, 1) : Math.max(level - step, 0);
        if (next <= 0 && !this.wanted.has(key) && !held(key)) this.levels.delete(key);
        else this.levels.set(key, next);
        if (next !== (this.wanted.has(key) ? 1 : 0)) this.moving = true;
      }
      this.redraw();
      return this.moving;
    });
  }

  /** The k-th item's shapes to draw, and how visible each is. */
  shownBy(k: number): [number, number][] {
    return (this.order[k] ?? [])
      .filter((id) => this.levels.has(`${k}:${id}`))
      .map((id) => [id, applyEase(this.ease, this.levels.get(`${k}:${id}`)!, (f) => this.rt.fn(f))]);
  }
}

export class MtpReadout extends MtpPart {
  private say: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime): void {
    const readout = this.find(rt, "readout");
    // A text node of its own, so that the view's switch beside it stays.
    const text = document.createTextNode("");
    this.present(text);
    this.say = () => {
      text.data = String(rt.value(readout, "value"));
      const font = rt.objects[readout]!.attrs?.font ? (rt.value(readout, "font") as Record<string, unknown>) : null;
      for (const part of ["family", "style", "weight"]) {
        if (font?.[part] !== null && font?.[part] !== undefined) this.style.setProperty(`font-${part}`, String(font[part]));
      }
    };
    this.say();
  }

  protected update(): void {
    this.say();
  }
}

// Where an SVG's view box is on the page: the map from the view box as the unit square, y down, to
// client coordinates, inverted, and the view box's width over its height. Panning and zooming keep
// that ratio, and then the map stays the same.
interface Screen {
  back: Transform;
  aspect: number;
}

// Safari 26 on iOS leaves the CSS transforms of the HTML elements around an SVG out of
// getScreenCTM (WebKit bug 308970, fixed in Safari 27), so a page that turns a canvas with CSS got
// drags that went the wrong way (mtp-fuy1). The browser does draw the SVG turned, so this measures
// where it draws three marks at corners of the view box. The center of a circle's bounding box is
// where its center is drawn under any transform of the plane. The marks are on the page only
// while they are measured.
function screenOf(svg: SVGSVGElement): Screen | null {
  const box = svg.viewBox?.baseVal;
  if (!box || !box.width || !box.height || !svg.isConnected) return null;
  const marks = document.createElementNS(SVG_NS, "g");
  for (const [k, v] of Object.entries({ "aria-hidden": "true", "pointer-events": "none", fill: "none", stroke: "none" })) {
    marks.setAttribute(k, v);
  }
  const r = Math.min(Math.abs(box.width), Math.abs(box.height)) / 100;
  const circles = [
    [0, 0],
    [1, 0],
    [0, 1],
  ].map(([u, v]) => {
    const c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("cx", String(box.x + u! * box.width));
    c.setAttribute("cy", String(box.y + v! * box.height));
    c.setAttribute("r", String(r));
    marks.append(c);
    return c;
  });
  svg.append(marks);
  const [o, x, y] = circles.map((c) => {
    const b = c.getBoundingClientRect();
    return [b.left + b.width / 2, b.top + b.height / 2] as [number, number];
  }) as [[number, number], [number, number], [number, number]];
  marks.remove();
  const map = [x[0] - o[0], x[1] - o[1], y[0] - o[0], y[1] - o[1], o[0], o[1]];
  const det = map[0]! * map[3]! - map[1]! * map[2]!;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-9) return null;
  return { back: invert(map), aspect: box.width / box.height };
}

// A formula's LaTeX is typeset again at most this often while a term's content changes, so a
// value that changes every frame does not typeset every frame.
const RETYPESET_MS = 100;
const SVG_NS = "http://www.w3.org/2000/svg";

/** Shows a formula (docs/reference.md, "Formulas"): its LaTeX typeset by MathJax, inside a
 * paragraph or as a block. Each term follows its attributes, and its on-click, on-enter and
 * on-leave play when the reader clicks it or the pointer comes onto it or goes off it. */
export class MtpDisplay extends MtpPart {
  /** The LaTeX typeset last. */
  latex = "";
  private show: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const display = this.find(rt, "display");
    const view = rt.objects[display]!;
    const formula = rt.objects[view.formula!]!;
    const terms = (formula.members ?? []).map((id) => ({ id, name: rt.objects[id]!.term! }));
    const clicks = model.clicks!;
    const hovers = (kind: string, id: number) =>
      rt.objects.filter((o) => o.kind === kind && o.shape === id && heardIn(o, display, rt) && holds(rt, o.active));
    const play = (listeners: Obj[]) => {
      for (const listener of listeners) {
        const player = playerFor(rt, listener);
        if (player) scheduler.start(player, listener, howOf(listener, true));
      }
    };
    const block = view.as !== "inline";
    this.style.display = block ? "block" : "inline";
    // Each term's element and its box before any adornment, in MathJax's units: 1000 an em.
    let marked = new Map<number, { el: SVGGElement; box: DOMRect | null }>();
    const wanted = () =>
      latexOf(
        formula.tex!,
        (name) => {
          const t = terms.find((x) => x.name === name);
          return t && rt.objects[t.id]!.attrs?.tex ? String(rt.value(t.id, "tex")) : undefined;
        },
        (name) => {
          const t = terms.find((x) => x.name === name);
          return t === undefined || Boolean(rt.value(t.id, "exists"));
        },
      );
    const render = () => {
      this.latex = wanted();
      const node = typeset(this.latex, block);
      this.present(node);
      marked = new Map();
      for (const { id, name } of terms) {
        const el = node.querySelector(`.${termClass(name)}`) as SVGGElement | null;
        if (!el) continue;
        el.setAttribute("data-mtp-id", String(id));
        marked.set(id, { el, box: typeof el.getBBox === "function" ? el.getBBox() : null });
        el.addEventListener("click", (event) => {
          const listeners = clicks.find(id, display);
          play(listeners);
          // An enclosing term hears the click too, unless this one stops it.
          if (listeners.some((l) => holds(rt, l["stop-propagation"], false))) event.stopPropagation();
        });
        el.addEventListener("pointerenter", () => play(hovers("on-enter", id)));
        el.addEventListener("pointerleave", () => play(hovers("on-leave", id)));
      }
    };
    const look = () => {
      const em = Number.parseFloat(getComputedStyle(this).fontSize) || 16;
      const units = (px: unknown) => (Number(px) * 1000) / em;
      for (const [id, { el, box }] of marked) {
        const fill = rt.value(id, "fill");
        if (fill === null || fill === undefined) el.style.removeProperty("color");
        else el.style.color = String(fill);
        el.style.opacity = String(rt.value(id, "opacity"));
        el.style.cursor = clicks.find(id, display).length ? "pointer" : "";
        let rect = el.querySelector(":scope > rect.mtp-term-box");
        if (!rect) {
          rect = document.createElementNS(SVG_NS, "rect");
          rect.setAttribute("class", "mtp-term-box");
          // The whole box is the term's, even unpainted, so the pointer between its glyphs is on
          // it.
          rect.setAttribute("pointer-events", "all");
          el.insertBefore(rect, el.firstChild);
        }
        const pad = units(rt.value(id, "padding"));
        const b = box ?? { x: 0, y: 0, width: 0, height: 0 };
        const background = rt.value(id, "background");
        const outline = rt.value(id, "outline");
        const at: Record<string, string | number> = {
          x: b.x - pad,
          y: b.y - pad,
          width: b.width + 2 * pad,
          height: b.height + 2 * pad,
          rx: units(rt.value(id, "rounding")),
          fill: background === null || background === undefined ? "none" : String(background),
          stroke: outline === null || outline === undefined ? "none" : String(outline),
          "stroke-width": units(rt.value(id, "outline-width")),
        };
        for (const [k, v] of Object.entries(at)) rect.setAttribute(k, String(v));
      }
    };
    let last = Number.NEGATIVE_INFINITY;
    let waiting = false;
    const again = (ms: number) => {
      if (ms - last < RETYPESET_MS) {
        frames.request(again);
        return;
      }
      waiting = false;
      last = ms;
      render();
      look();
    };
    this.show = () => {
      if (wanted() !== this.latex && !waiting) {
        waiting = true;
        frames.request(again);
      }
      look();
    };
    render();
    look();
  }

  protected update(): void {
    this.show();
  }
}

function labelOf(rt: Runtime, id: number): string {
  return String(rt.value(id, "label"));
}

/** What a control shows as its label: its text, or, for one given as a TeX string, (label $'…'),
 * its LaTeX typeset as a formula is, named for a screen reader by the LaTeX. follow() brings it up
 * to date with the expression it is given. */
function labelPart(rt: Runtime, id: number): { node: Node; follow: () => void } {
  return textPart(() => labelOf(rt, id), Boolean(rt.objects[id]!["label-tex"]));
}

/** A text that follow() brings up to date with what text() gives: plain, or LaTeX typeset. */
function textPart(text: () => string, tex: boolean): { node: Node; follow: () => void } {
  if (!tex) {
    const node = document.createTextNode(text());
    return {
      node,
      follow: () => {
        const now = text();
        if (node.data !== now) node.data = now;
      },
    };
  }
  const math = document.createElement("span");
  math.className = "mtp-label-math";
  math.setAttribute("role", "img");
  let shown: string | null = null;
  const follow = () => {
    const latex = text();
    if (latex === shown) return;
    shown = latex;
    math.replaceChildren(typeset(latex, false));
    math.setAttribute("aria-label", latex);
  };
  follow();
  return { node: math, follow };
}

/** The copy of each play or stepper that moved it last. Two copies of one control on a page, such
 * as a block pinned beside the text, are two writers, decided between as any two are
 * (docs/reference.md, "Concurrency"), so only the one moved last writes the control's own step
 * and playing. */
const movers = new WeakMap<Runtime, Map<number, Element>>();

function moves(rt: Runtime, id: number, el: Element): void {
  let byId = movers.get(rt);
  if (!byId) movers.set(rt, (byId = new Map()));
  byId.set(id, el);
}

function movedLastBy(rt: Runtime, id: number, el: Element): boolean {
  return movers.get(rt)?.get(id) === el;
}

// Whether the reader has moved no copy of a control yet: each copy then shows state 0, and
// writes the same.
function unmoved(rt: Runtime, id: number): boolean {
  return !movers.get(rt)?.has(id);
}

// The canvases with a copy on the page, by runtime. A control waits only for those: a canvas
// not on the page never comes into view, so it would never be ready.
const placed = new WeakMap<Runtime, Set<number>>();

/** Whether a control takes input: it is active, and every canvas it belongs to that is on the
 * page is ready (docs/canvas-lifecycle.md, rule 5). */
function usable(rt: Runtime, id: number): boolean {
  const here = placed.get(rt);
  return activeOf(rt, id) && !(rt.objects[id]!.canvases ?? []).some((c) => rt.unready.has(c) && here?.has(c));
}

/** Whether a writer is active, so it can be triggered: always, unless its active is false. */
function activeOf(rt: Runtime, id: number): boolean {
  const active = rt.objects[id]!.active;
  return active === null || active === undefined || Boolean(rt.evaluate(active));
}

export class MtpSlider extends MtpPart {
  private follow: () => void = () => {};
  private gate: () => void = () => {};
  private named: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "slider");
    // A slider that names its target is a jumper (docs/spec/controls.md). One with an animation
    // is of the older form, which the runtime still reads.
    const target = rt.objects[id]!.target;
    if (target) {
      this.follow = trackControl(this, rt, scheduler, id, [target], (state) => this.pageState(state));
      return;
    }
    const player = playerFor(rt, rt.objects[id]!);
    const how = howOf(rt.objects[id]!, true);
    const input = document.createElement("input");
    input.type = "range";
    const stops = rt.objects[id]!.attrs?.stops ? (rt.value(id, "stops") as number) : null;
    // With (stops n) the knob stops at n evenly spaced stops.
    input.min = "0";
    input.max = stops === null ? "1000" : String(stops - 1);
    input.step = "1";
    input.value = String(Math.round((rt.value(id, "position") as number) * Number(input.max)));
    // How far along the knob is, which fills the track up to it.
    const fill = () => input.style.setProperty("--u", String(Number(input.value) / Number(input.max)));
    fill();
    input.addEventListener("input", () => {
      if (!usable(rt, id)) return;
      const u = Number(input.value) / Number(input.max);
      const write = () => {
        player?.scrub(u);
        rt.write(id, "position", u);
      };
      if (cut || (player && !scheduler.instant(this, how, write))) {
        // Refused, or cancelled while held: the knob goes back to where it was.
        input.value = String(Math.round((rt.value(id, "position") as number) * Number(input.max)));
        fill();
        return;
      }
      if (!player) write();
      fill();
    });
    input.addEventListener("change", () => player?.release());
    // A slider follows its target: when another writer changes the one variable or attribute its animation
    // moves, the knob goes to the position whose value is closest (reference.md, "Controls").
    let scrubbing = false;
    // A press on the track or the knob through the release is one gesture, triggered by the press
    // (the author, 2026-11-13): its first write jumps to the pressed point. Cancelled while held,
    // it writes nothing more until the release. An arrow key is a trigger of the reader's of its
    // own, an animation of one move that takes no time.
    let cut = false;
    const release = () => {
      if (!scrubbing) return;
      scrubbing = false;
      cut = false;
      scheduler.letGo(this);
      this.gate();
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
    input.addEventListener("pointerdown", () => {
      scrubbing = true;
      cut = false;
      this.gate();
      if (player && usable(rt, id)) scheduler.grip(this, how, () => (cut = true));
      // The release may come anywhere on the page, so the window hears it too.
      window.addEventListener("pointerup", release);
      window.addEventListener("pointercancel", release);
    });
    input.addEventListener("pointerup", release);
    input.addEventListener("pointercancel", release);
    this.follow = () => {
      if (scrubbing || !player || player.targets.length !== 1) return;
      const [tid, tattr] = player.targets[0]!.split(":");
      const now = rt.value(Number(tid), tattr === "" ? null : tattr!);
      const max = Number(input.max);
      let best = Number(input.value);
      let gap = Infinity;
      const values = player.valuesAt(max);
      for (let n = 0; n <= max; n++) {
        const d = distance(values[n], now);
        if (d < gap) [best, gap] = [n, d];
      }
      input.value = String(best);
      fill();
      rt.write(id, "position", best / max);
    };
    this.follow();
    input.dataset.mtpInput = "track";
    this.gate = () => {
      input.disabled = !usable(rt, id);
      this.pageState({ inactive: !activeOf(rt, id), held: scrubbing });
    };
    this.gate();
    // The label follows what it is given, as anything bound does.
    const text = labelPart(rt, id);
    this.named = text.follow;
    // The label sits above the track: a label whose width changes as it follows its value would
    // otherwise move the track under the pointer while it drags.
    const label = document.createElement("label");
    label.append(text.node, input);
    // Round values across the range the knob covers, each where the knob gives it. The labels
    // are drawn from data-value, so the control's text stays its label.
    const ticks = player ? placeTicks((u) => player.valueAt(u)) : [];
    if (ticks.length) {
      const row = document.createElement("div");
      row.className = "mtp-ticks";
      row.setAttribute("aria-hidden", "true");
      for (const t of ticks) {
        const mark = document.createElement("span");
        mark.dataset.value = String(t.value);
        mark.style.setProperty("--u", String(Number(t.u.toFixed(6))));
        row.append(mark);
      }
      label.append(row);
    }
    this.replaceChildren(label);
  }

  protected update(): void {
    this.follow();
    this.gate();
    this.named();
  }
}

function distance(a: unknown, b: unknown): number {
  if (typeof a === "number" && typeof b === "number") return Math.abs(a - b);
  if (Array.isArray(a) && Array.isArray(b)) return Math.hypot(...a.map((x: number, i) => x - (b[i] as number)));
  return a === b ? 0 : 1;
}

export class MtpButton extends MtpPart {
  private gate: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "button");
    const button = document.createElement("button");
    const text = labelPart(rt, id);
    button.append(text.node);
    // A press plays the animation from the start; a press while it runs starts it again.
    button.addEventListener("click", () => {
      if (!usable(rt, id)) return;
      const player = playerFor(rt, rt.objects[id]!);
      if (player) scheduler.start(player, this, howOf(rt.objects[id]!, true));
    });
    button.dataset.mtpInput = "button";
    this.gate = () => {
      button.disabled = !usable(rt, id);
      this.pageState({ inactive: !activeOf(rt, id) });
      text.follow();
    };
    this.gate();
    this.replaceChildren(button);
  }

  protected update(): void {
    this.gate();
  }
}

// The play button's icons (Tabler's player-play-filled, player-pause-filled and reload), drawn in
// the color of the page on the button's ink.
const PLAY_ICON =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4v16a1 1 0 0 0 1.524 .852l13 -8a1 1 0 0 0 0 -1.704l-13 -8a1 1 0 0 0 -1.524 .852z"/></svg>';
const PAUSE_ICON =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h2a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2z"/><path d="M17 4h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h2a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2z"/></svg>';
const REPLAY_ICON =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.933 13.041a8 8 0 1 1 -9.925 -8.788c3.899 -1 7.935 1.007 9.425 4.747"/><path d="M20 4v5h-5"/></svg>';
// How far, in CSS pixels, a mouse may move on the bars and still tap one rather than drag.
const MOUSE_SLOP = 3;
// How close, in seconds, two times along an animation count as the same.
const EPS = 1e-9;

// Whether keys pressed on el are its own: a field takes Space and the arrows, and so does any
// other control.
function takesKeys(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return el.isContentEditable || el.closest(TAKE_KEYS) !== null;
}
const TAKE_KEYS = [
  "input, textarea, select, button, [role=slider], [role=spinbutton], [role=listbox]",
  "mtp-slider, mtp-toggle, mtp-button, mtp-range-slider, mtp-dial, mtp-number-field, mtp-text-field, mtp-select, mtp-multi-select",
].join(", ");
// What has the keys of a play: on a page with only one, they work from anywhere on it.
const KEYED = "mtp-play, mtp-stepper";

/** The step, from 1, that a time along an animation is in: the last one started by then, so a
 * rest after a step is still that step's. */
function stepAt(spans: Span[], t: number): number {
  let k = 1;
  spans.forEach((s, j) => {
    if (t >= s.start - EPS * Math.max(1, s.start)) k = j + 1;
  });
  return k;
}

// How soon, in milliseconds, after a step starts playing, a press of the left arrow or "‹" goes
// back one step further, as a music player's back button does (the author, 2026-11-13).
const BACK_MS = 300;

/** When the step that plays now started playing: at the press that started it, or in the frame
 * in which a running play's position entered it. */
function stepStarts() {
  let step = 0;
  let at = -Infinity;
  const started = (k: number) => {
    step = k;
    at = frames.now();
  };
  return {
    started,
    // Called on each refresh while running, so the time of a step reached by playing on is the
    // time of the frame in which the play reached it.
    playing: (k: number) => {
      if (k !== step) started(k);
    },
    soon: (k: number) => k === step && frames.now() - at < BACK_MS,
  };
}

/** Whether a paused time is partway through a step, so the step is the one paused in rather than
 * one read from the scene: past the start, and not at the end of a step. */
function partway(spans: Span[], t: number): boolean {
  const near = (x: number) => Math.abs(t - x) <= EPS * Math.max(1, Math.abs(x));
  return t > spans[0]!.start && !near(spans[0]!.start) && !spans.some((s) => near(s.end));
}

/**
 * A play (docs/reference.md, "Controls"; the author, 2026-11-13): a button, then a bar with a
 * knob, one bar per step with (buttons true) and the step count after them. Its step is read
 * from the scene: the highest step whose state the scene is in, or 0 in explore mode, except
 * while it plays or is paused partway through a step. Each input is a listener whose effect sets
 * a state j and plays steps j + 1 to N.
 */
export class MtpPlay extends MtpPart {
  private refresh: () => void = () => {};
  private onPage: ((event: KeyboardEvent) => void) | null = null;
  private unwatch: () => void = () => {};

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = null;
    this.unwatch();
  }

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "play");
    const obj = rt.objects[id]!;
    const layout = playerFor(rt, obj);
    if (!layout) {
      this.replaceChildren();
      return;
    }
    const split = Boolean(rt.value(id, "buttons"));
    const all = layout.spans;
    const n = all.length;
    const spans = split ? all : [{ start: all[0]!.start, end: all.at(-1)!.end }];
    const labels = obj.labels ?? [];
    const how = howOf(obj, true);
    // The player of this copy's effect while it runs, is paused or is dragged.
    let player: Player | null = null;
    let dragging = false;
    const starts = stepStarts();

    const paused = () => {
      const p = scheduler.pausedOf(this);
      return p !== null && !p.done && partway(all, p.position);
    };
    const moving = () => scheduler.running(this) || dragging || paused();
    const stepNow = () => (moving() && player ? stepAt(all, player.position) : layout.stepNowIn());
    // Set state j, then play steps j + 1 to N.
    const go = (j: number) => {
      if (!usable(rt, id)) return;
      moves(rt, id, this);
      player = playerFor(rt, obj)!;
      starts.started(j + 1);
      scheduler.start(player, this, how, all[j]!.start, () => layout.setState(j));
      this.refresh();
    };
    const press = () => {
      if (!usable(rt, id)) return;
      moves(rt, id, this);
      if (scheduler.running(this)) scheduler.pause(this);
      else if (paused()) scheduler.resume(this, how);
      else {
        const k = stepNow();
        go(k < n ? k : 0);
      }
      this.refresh();
    };

    const play = document.createElement("button");
    play.type = "button";
    play.className = "mtp-play-button";
    play.dataset.mtpInput = "button";
    play.addEventListener("click", press);
    const track = document.createElement("div");
    track.className = "mtp-bars";
    track.tabIndex = 0;
    track.setAttribute("role", "slider");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", String(n));
    const bars = spans.map((s, j) => {
      const bar = document.createElement("span");
      bar.className = "mtp-bar";
      bar.dataset.mtpInput = `bar-${j + 1}`;
      // A step that takes no time still gets a sliver, so it can be seen and tapped.
      bar.style.flexGrow = String(Math.max(s.end - s.start, 0.05 * (all.at(-1)!.end || 1)));
      bar.style.setProperty("--u", "0");
      track.append(bar);
      return bar;
    });
    const knob = document.createElement("span");
    knob.className = "mtp-knob";
    knob.setAttribute("aria-hidden", "true");
    const pill = document.createElement("span");
    pill.className = "mtp-exploring";
    pill.textContent = "Exploring";
    pill.setAttribute("aria-hidden", "true");
    track.append(pill);
    // After the bars, with (buttons true): the count and the step's label, as "2 / 4 · A third
    // of a turn" (the author, 2026-11-13). The text of every state is laid in the same place,
    // hidden, so the room is as wide as the longest and the row never changes length.
    const textOf = (k: number) => (k === 0 ? `– / ${n}` : `${k} / ${n}${labels[k - 1] ? ` · ${labels[k - 1]}` : ""}`);
    const count = split ? document.createElement("span") : null;
    const after = split ? document.createElement("div") : null;
    if (count && after) {
      count.className = "mtp-count";
      count.setAttribute("aria-hidden", "true");
      after.className = "mtp-after";
      for (let k = 0; k <= n; k++) {
        const room = document.createElement("span");
        room.className = "mtp-count-room";
        room.setAttribute("aria-hidden", "true");
        room.textContent = textOf(k);
        after.append(room);
      }
      after.append(count);
    }

    // Keys (the author, 2026-11-13): Space is the button. At step k the right arrow is a tap on
    // bar k + 1 and the left arrow one on bar k, or on bar k - 1 when pressed soon after step k
    // started. Each is off where that bar does not exist. Without (buttons true) there are no
    // arrow keys.
    const keys: Record<string, () => boolean> = {
      " ": () => (press(), true),
      ArrowRight: () => {
        const k = stepNow();
        if (!split) return false;
        if (k < n) go(k);
        return true;
      },
      ArrowLeft: () => {
        const k = stepNow();
        if (!split) return false;
        if (k > 0) go(starts.soon(k) && k > 1 ? k - 2 : k - 1);
        return true;
      },
    };
    const onKey = (event: KeyboardEvent) => {
      const act = keys[event.key];
      if (!act || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.repeat || !usable(rt, id)) {
        if (event.key === " " || split) event.preventDefault();
        return;
      }
      if (act()) event.preventDefault();
    };
    this.addEventListener("keydown", (event) => {
      // The play button presses itself on Space, as any button does.
      if (event.key === " " && event.target === play) return;
      onKey(event);
    });
    // On a page with one play or stepper, as when recording it, the keys work from anywhere on the page,
    // unless what has focus takes keys of its own.
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = (event) => {
      if (this.contains(event.target as Node) || document.querySelectorAll(KEYED).length !== 1) return;
      if (takesKeys(event.target) || takesKeys(document.activeElement)) return;
      onKey(event);
    };
    document.addEventListener("keydown", this.onPage);

    // The bar nearest x, and the time x stands for along it.
    const nearest = (x: number): number => {
      let best = 0;
      let gap = Infinity;
      bars.forEach((bar, k) => {
        const r = bar.getBoundingClientRect();
        const d = x < r.left ? r.left - x : x > r.right ? x - r.right : 0;
        if (d < gap) [best, gap] = [k, d];
      });
      return best;
    };
    const timeAt = (x: number): number => {
      const k = nearest(x);
      const r = bars[k]!.getBoundingClientRect();
      const u = r.width > 0 ? Math.min(Math.max((x - r.left) / r.width, 0), 1) : 0;
      return spans[k]!.start + u * (spans[k]!.end - spans[k]!.start);
    };
    // A press on the bars is a tap, or once it moves past the slop, a drag (a gesture, the author,
    // 2026-11-13): at each point it sets state i - 1 for the step i under the pointer, then each
    // move of step i at its value there, and on release the play is paused there.
    let held: { x: number; slop: number; was: boolean; moved: boolean; cut: boolean } | null = null;
    track.addEventListener("pointerdown", (event) => {
      if (!usable(rt, id) || event.button !== 0) return;
      const was = scheduler.running(this);
      if (was) scheduler.pause(this);
      held = { x: event.clientX, slop: event.pointerType === "mouse" ? MOUSE_SLOP : TOUCH_SLOP, was, moved: false, cut: false };
      track.setPointerCapture?.(event.pointerId);
      track.classList.add("mtp-dragging");
      event.preventDefault();
    });
    track.addEventListener("pointermove", (event) => {
      const h = held;
      if (!h || h.cut) return;
      if (!h.moved && Math.abs(event.clientX - h.x) <= h.slop) return;
      if (!h.moved) {
        h.moved = true;
        dragging = true;
        moves(rt, id, this);
        player = playerFor(rt, obj)!;
        scheduler.scrub(player, this, how, () => {
          h.cut = true;
          dragging = false;
        });
      }
      const t = timeAt(event.clientX);
      rt.jump(() => scheduler.scrubTo(this, t, () => layout.setState(stepAt(all, t) - 1)));
      this.refresh();
    });
    const release = (event: PointerEvent, tap: boolean) => {
      const h = held;
      if (!h) return;
      held = null;
      track.classList.remove("mtp-dragging");
      if (h.moved) {
        dragging = false;
        if (!h.cut) scheduler.pause(this);
      } else if (tap) go(split ? nearest(event.clientX) : 0);
      else if (h.was) scheduler.resume(this, how);
      this.refresh();
    };
    track.addEventListener("pointerup", (event) => release(event, true));
    track.addEventListener("pointercancel", (event) => release(event, false));

    // A pause ends when another writer writes what the play moves (the author, 2026-11-12;
    // which writes end it is not decided yet).
    scheduler.watch(this, layout.targets, () => {
      if (!scheduler.running(this) && !dragging && scheduler.pausedOf(this)) scheduler.letGo(this);
    });
    this.unwatch = () => scheduler.unwatch(this);

    this.refresh = () => {
      const running = scheduler.running(this);
      const active = usable(rt, id);
      const shown = moving() ? player : null;
      const k = stepNow();
      if (running) starts.playing(k);
      const exploring = k === 0 && !shown;
      // How far along the animation the bars stand: where the player stands, or the end of the
      // step read from the scene.
      const t = shown ? shown.position : k > 0 ? all[k - 1]!.end : all[0]!.start;
      const last = k === n && !shown;
      play.innerHTML = running ? PAUSE_ICON : last ? REPLAY_ICON : PLAY_ICON;
      play.classList.toggle("mtp-replay", !running && last);
      play.setAttribute("aria-label", running ? "pause" : labelOf(rt, id));
      play.disabled = !active;
      track.setAttribute("aria-disabled", String(!active));
      let at = 0;
      bars.forEach((bar, j) => {
        const s = spans[j]!;
        const u = s.end > s.start ? Math.min(Math.max((t - s.start) / (s.end - s.start), 0), 1) : t >= s.start - EPS && !exploring ? 1 : 0;
        bar.style.setProperty("--u", String(Number(u.toFixed(4))));
        if (t >= s.start - EPS) at = j;
      });
      // The knob sits where the fill ends, on the bar it is in; in explore mode, an empty ring at
      // the left end.
      if (exploring) at = 0;
      if (knob.parentElement !== bars[at]) bars[at]!.append(knob);
      knob.classList.toggle("mtp-empty", exploring);
      knob.classList.toggle("mtp-end", at === bars.length - 1 && t >= spans.at(-1)!.end - EPS);
      pill.hidden = !exploring;
      if (count) count.textContent = textOf(exploring ? 0 : k);
      const text = exploring ? `${n} ${n === 1 ? "step" : "steps"}` : textOf(k);
      track.setAttribute("aria-label", labelOf(rt, id));
      track.setAttribute("aria-valuenow", String(k));
      track.setAttribute("aria-valuetext", text);
      // The writes come before mtp-state, so that a page listener on it reads the step and
      // playing values that the attributes show. together holds back the change until after
      // mtp-state, so mtp-state still fires before mtp-change (mtp-gvrf.12).
      rt.together(() => {
        if (movedLastBy(rt, id, this) || unmoved(rt, id)) {
          if (rt.value(id, "playing") !== running) rt.write(id, "playing", running);
          if (rt.value(id, "step") !== k) rt.write(id, "step", k);
        }
        this.pageState({ inactive: !activeOf(rt, id), step: String(k), playing: running, exploring });
      });
    };
    const indicator = document.createElement("div");
    indicator.className = "mtp-indicator";
    indicator.append(track);
    this.replaceChildren(play, indicator, ...(after ? [after] : []));
    this.refresh();
  }

  protected update(): void {
    this.refresh();
  }
}

// A stepper's buttons' icons (Tabler's chevron-left and chevron-right), drawn as the play
// button's are.
const BACK_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6l6 6"/></svg>';
const NEXT_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6l-6 6"/></svg>';

/**
 * A stepper (docs/reference.md, "Controls"; the author, 2026-11-13): "‹", a dot per step, "›"
 * and the step count. Its step is read from the scene as a play's is. Dot i sets state i - 1 and
 * plays step i; "›" is the dot after the step, and "‹" the dot of the step, which plays it again,
 * or the dot before it when pressed soon after the step started.
 */
export class MtpStepper extends MtpPart {
  private refresh: () => void = () => {};
  private onPage: ((event: KeyboardEvent) => void) | null = null;

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = null;
  }

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "stepper");
    const obj = rt.objects[id]!;
    const layout = playerFor(rt, obj);
    if (!layout) {
      this.replaceChildren();
      return;
    }
    const all = layout.spans;
    const n = all.length;
    const how = howOf(obj, true);
    let player: Player | null = null;
    const starts = stepStarts();

    const stepNow = () => (scheduler.running(this) && player ? stepAt(all, player.position) : layout.stepNowIn());
    // Dot i: set state i - 1, then play step i and stop at its end.
    const go = (i: number) => {
      if (!usable(rt, id) || i < 1 || i > n) return;
      moves(rt, id, this);
      player = playerFor(rt, obj)!;
      player.holdFrom(i);
      starts.started(i);
      scheduler.start(player, this, how, all[i - 1]!.start, () => layout.setState(i - 1), all[i - 1]!.end);
      this.refresh();
    };
    const forward = () => go(stepNow() + 1);
    const backward = () => {
      const k = stepNow();
      if (k > 0) go(starts.soon(k) && k > 1 ? k - 1 : k);
    };

    const round = (name: string, icon: string, label: string, act: () => void) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `mtp-step-button mtp-${name}`;
      b.dataset.mtpInput = name;
      b.innerHTML = icon;
      b.setAttribute("aria-label", label);
      b.addEventListener("click", act);
      return b;
    };
    const back = round("back", BACK_ICON, "previous step", backward);
    const next = round("next", NEXT_ICON, "next step", forward);
    const group = document.createElement("div");
    group.className = "mtp-dots";
    group.setAttribute("role", "group");
    const dots = all.map((_, j) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "mtp-dot";
      dot.dataset.mtpInput = `dot-${j + 1}`;
      dot.setAttribute("aria-label", `step ${j + 1}`);
      dot.addEventListener("click", () => go(j + 1));
      group.append(dot);
      return dot;
    });
    // The pill reading Exploring sits on the dots in explore mode, as on a play's bars, and keeps
    // its room while hidden, so the dots are never narrower than it (the author, 2026-11-13).
    const pill = document.createElement("span");
    pill.className = "mtp-exploring";
    pill.textContent = "Exploring";
    pill.setAttribute("aria-hidden", "true");
    const area = document.createElement("div");
    area.className = "mtp-dot-area";
    area.append(group, pill);
    // The count beside the dots; the dots' group already says it to a screen reader.
    const count = document.createElement("span");
    count.className = "mtp-count";
    count.setAttribute("aria-hidden", "true");

    // The keys of a stepper: the arrows are "›" and "‹".
    const keys: Record<string, () => void> = { ArrowRight: forward, ArrowLeft: backward };
    const onKey = (event: KeyboardEvent) => {
      const act = keys[event.key];
      if (!act || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      if (!event.repeat && usable(rt, id)) act();
    };
    this.addEventListener("keydown", onKey);
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = (event) => {
      if (this.contains(event.target as Node) || document.querySelectorAll(KEYED).length !== 1) return;
      if (takesKeys(event.target) || takesKeys(document.activeElement)) return;
      onKey(event);
    };
    document.addEventListener("keydown", this.onPage);

    this.refresh = () => {
      const running = scheduler.running(this);
      const active = usable(rt, id);
      const k = stepNow();
      const exploring = k === 0 && !running;
      back.disabled = !active || k === 0;
      next.disabled = !active || k === n;
      dots.forEach((dot, j) => {
        dot.disabled = !active;
        dot.classList.toggle("mtp-passed", j + 1 < k);
        if (j + 1 === k) dot.setAttribute("aria-current", "step");
        else dot.removeAttribute("aria-current");
      });
      const label = labelOf(rt, id);
      count.textContent = `${exploring ? "–" : k} / ${n}`;
      pill.hidden = !exploring;
      group.setAttribute("aria-label", k ? `${label}: step ${k} of ${n}` : `${label}: ${n} ${n === 1 ? "step" : "steps"}`);
      // The writes come before mtp-state for the reason given in a play's refresh (mtp-gvrf.12).
      rt.together(() => {
        if (movedLastBy(rt, id, this) || unmoved(rt, id)) {
          if (rt.value(id, "playing") !== running) rt.write(id, "playing", running);
          if (rt.value(id, "step") !== k) rt.write(id, "step", k);
        }
        this.pageState({ inactive: !activeOf(rt, id), step: String(k), playing: running, exploring });
      });
    };
    this.replaceChildren(back, area, next, count);
    this.refresh();
  }

  protected update(): void {
    this.refresh();
  }
}

export class MtpToggle extends MtpPart {
  private input: HTMLInputElement | null = null;
  private show: () => void = () => {};
  private named: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "toggle");
    const obj = rt.objects[id]!;
    // A toggle always writes a bool variable or attribute (mtp-0lzp).
    const target = obj.target!;
    const input = document.createElement("input");
    input.type = "checkbox";
    const members = rt.objects[target[0]]!.kind === "group" ? rt.objects[target[0]]!.members! : null;
    input.dataset.mtpInput = "box";
    this.show = () => {
      input.disabled = !usable(rt, id);
      this.pageState({ inactive: !activeOf(rt, id) });
      if (members) {
        const values = members.map((m) => Boolean(rt.value(m, target[1])));
        // A mixed state when the members differ.
        input.indeterminate = values.some(Boolean) && !values.every(Boolean);
        input.checked = values.every(Boolean);
      } else {
        input.checked = Boolean(rt.value(id, "value"));
      }
    };
    input.addEventListener("change", () => {
      if (!usable(rt, id)) {
        this.show();
        return;
      }
      // A click writes (not TARGET) (docs/spec/controls.md, rule toggle), and on a mixed toggle
      // sets every member to true.
      const v = members ? input.indeterminate || input.checked : !rt.value(id, "value");
      const how = howOf(obj, true);
      const player = playerFor(rt, obj);
      // One effect (the author, 2026-11-13): the flip, a move that takes no time, then the
      // toggle's animation, so the toggle owns its bool until the animation ends. Each write is
      // decided as any writer's is: a flip that is rejected leaves the box as the bool is.
      const flip = () => rt.write(target[0], target[1], v);
      if (player) scheduler.start(player, this, how, 0, flip);
      else scheduler.instant(this, how, flip);
      this.show();
    });
    this.input = input;
    this.show();
    // The label follows what it is given, as anything bound does.
    const text = labelPart(rt, id);
    this.named = text.follow;
    const label = document.createElement("label");
    label.append(input, text.node);
    this.replaceChildren(label);
  }

  protected update(): void {
    this.show();
    this.named();
  }
}

// The jumpers (docs/spec/controls.md, rule jumpers-and-movers): each writes one value to its
// target by a jump each time the reader acts on it, and always shows the target's value.

type Target = [number, string | null];
type PageState = (state: Record<string, string | boolean>) => void;

// Ids for the parts that refer to each other, such as a box and its label.
let parts = 0;
const partId = () => `mtp-part-${++parts}`;

// How far, in CSS pixels, the pointer moves while scrubbing a number field for each step. The
// same on every field (the author, 2026-11-23).
const SCRUB_PX = 4;
// How long, in milliseconds, the red outline of a refused or changed commit stays.
const REFUSED_MS = 1500;
// The half width of a thumb: its center runs from this far in from each end of a track.
const THUMB_HALF = 8;

/** The type of a target, as written in the .mtpc. */
function targetType(rt: Runtime, [id, attr]: Target): Type {
  return rt.typeOf(rt.holders(id, attr)[0] ?? id, attr) ?? "real";
}

/** A value brought into the writer's guards on its target (docs/spec/well-formedness.md, rule
 * writer-guards). */
function guarded(rt: Runtime, writer: Obj, [id, attr]: Target, v: unknown): unknown {
  if (typeof v !== "number") return v;
  let x = v;
  for (const c of writer.conditions ?? []) if (c.target[0] === id && c.target[1] === attr) x = rt.clamp(c, x);
  return x;
}

/** One jump of a control's target, decided as every write of a writer is (docs/concurrency-model.md).
 * Gives false when the write was rejected. */
function jumpTo(rt: Runtime, scheduler: Scheduler, source: object, writer: Obj, target: Target, v: unknown): boolean {
  return scheduler.instant(source, howOf(writer, true), () => rt.write(target[0], target[1], guarded(rt, writer, target, v)));
}

/**
 * A press, the moves after it and its release, as one gesture of the reader's: a held writer
 * until the release (docs/concurrency-model.md). move is called at the press and at each move,
 * and no longer once another writer cancels the gesture. The release may come anywhere on the
 * page, so the window hears the moves and the release.
 */
function hold(source: object, scheduler: Scheduler, writer: Obj, down: PointerEvent, move: (e: PointerEvent) => void, end: () => void): void {
  let cut = false;
  scheduler.grip(source, howOf(writer, true), () => (cut = true));
  const onMove = (e: PointerEvent) => {
    if (!cut) move(e);
  };
  const release = () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", release);
    window.removeEventListener("pointercancel", release);
    scheduler.letGo(source);
    end();
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", release);
  window.addEventListener("pointercancel", release);
  move(down);
}

/** The control's label, in a span that its inputs name as their label. */
function labelSpan(rt: Runtime, id: number): { span: HTMLSpanElement; follow: () => void } {
  const text = labelPart(rt, id);
  const span = document.createElement("span");
  span.className = "mtp-label";
  span.id = partId();
  span.append(text.node);
  return { span, follow: text.follow };
}

/** A part that tells a screen reader of a refused commit, unseen. */
function liveRegion(): HTMLSpanElement {
  const live = document.createElement("span");
  live.className = "mtp-live";
  live.setAttribute("aria-live", "polite");
  return live;
}

/** Shows a red outline on a box for a moment, and tells a screen reader the same. */
function refuse(box: HTMLElement, live: HTMLElement, message: string): void {
  box.classList.remove("mtp-refused");
  clearTimeout(Number(box.dataset.mtpRefused ?? 0));
  box.classList.add("mtp-refused");
  box.dataset.mtpRefused = String(setTimeout(() => box.classList.remove("mtp-refused"), REFUSED_MS));
  live.textContent = message;
}

/** What a number is shown as, by its target's type, as a readout shows it with no format. */
function shownNumber(rt: Runtime, type: Type, v: unknown): string {
  return show(v, rt.core(type), "");
}

/** The arrow keys that move a thumb, as the ARIA slider pattern has them: a step up or down, or
 * to an end. */
function thumbKey(key: string): number | "start" | "end" | null {
  if (key === "ArrowRight" || key === "ArrowUp") return 1;
  if (key === "ArrowLeft" || key === "ArrowDown") return -1;
  if (key === "Home") return "start";
  if (key === "End") return "end";
  return null;
}

/** A thumb, a slider for assistive technology, that takes the keys. */
function makeThumb(input: string): HTMLSpanElement {
  const thumb = document.createElement("span");
  thumb.className = "mtp-thumb";
  thumb.setAttribute("role", "slider");
  thumb.dataset.mtpInput = input;
  return thumb;
}

function setThumb(thumb: HTMLElement, v: number, min: number, max: number, text: string, on: boolean): void {
  thumb.setAttribute("aria-valuenow", String(v));
  thumb.setAttribute("aria-valuemin", String(min));
  thumb.setAttribute("aria-valuemax", String(max));
  thumb.setAttribute("aria-valuetext", text);
  thumb.tabIndex = on ? 0 : -1;
  if (on) thumb.removeAttribute("aria-disabled");
  else thumb.setAttribute("aria-disabled", "true");
}

/** The ticks of a scale, as short lines under the track with their values, rebuilt only when
 * the values change. */
function tickRow(): { row: HTMLDivElement; set: (s: Scale, values: number[]) => void } {
  const row = document.createElement("div");
  row.className = "mtp-ticks";
  row.setAttribute("aria-hidden", "true");
  let shown = "";
  const set = (s: Scale, values: number[]) => {
    const key = JSON.stringify([s.lo, s.hi, values]);
    if (key === shown) return;
    shown = key;
    row.replaceChildren(
      ...values.map((v) => {
        const mark = document.createElement("span");
        mark.dataset.value = String(v);
        mark.style.setProperty("--u", String(Number(fractionOf(s, v).toFixed(6))));
        return mark;
      }),
    );
  };
  return { row, set };
}

/**
 * A slider that names its target, or a range slider (docs/spec/controls.md, rules slider-and-dial
 * and range-slider): a label, then a straight track with one thumb per target and its ticks. A
 * press on the track moves the nearer thumb there, a drag of a thumb moves it, and the arrow keys
 * step it. A range slider's thumb dragged into the other stops there. Gives what brings it up to
 * date.
 */
function trackControl(part: HTMLElement, rt: Runtime, scheduler: Scheduler, id: number, targets: Target[], state: PageState): () => void {
  const obj = rt.objects[id]!;
  const ranged = targets.length === 2;
  const label = labelSpan(rt, id);
  const track = document.createElement("div");
  track.className = "mtp-track";
  const fill = document.createElement("span");
  fill.className = "mtp-fill";
  track.append(fill);
  const thumbs = targets.map((_, k) => makeThumb(ranged ? (k === 0 ? "low" : "high") : "thumb"));
  track.append(...thumbs);
  track.dataset.mtpInput = "track";
  if (!ranged) thumbs[0]!.setAttribute("aria-labelledby", label.span.id);
  const ticks = tickRow();
  const wrap = document.createElement("div");
  wrap.className = "mtp-jumper";
  wrap.append(label.span, track, ticks.row);
  part.replaceChildren(wrap);

  const scale = (): Scale => {
    const step = rt.value(id, "step") as number | null;
    const int = targets.every((t) => rt.core(targetType(rt, t)) === "int");
    return { lo: rt.value(id, "from") as number, hi: rt.value(id, "to") as number, step, int, wrap: false };
  };
  const valueOfTarget = (k: number): number => {
    const v = rt.value(targets[k]![0], targets[k]![1]);
    return typeof v === "number" ? v : scale().lo;
  };
  let held = false;
  const refresh = () => {
    const s = scale();
    const on = usable(rt, id);
    const name = labelOf(rt, id);
    const u = targets.map((_, k) => fractionOf(s, valueOfTarget(k)));
    thumbs.forEach((thumb, k) => {
      const v = valueOfTarget(k);
      thumb.style.setProperty("--u", String(u[k]));
      setThumb(thumb, v, Math.min(s.lo, s.hi), Math.max(s.lo, s.hi), shownNumber(rt, targetType(rt, targets[k]!), v), on);
      if (ranged) thumb.setAttribute("aria-label", `${name}${name ? ", " : ""}${k === 0 ? "low" : "high"}`);
    });
    track.style.setProperty("--a", String(ranged ? Math.min(u[0]!, u[1]!) : 0));
    track.style.setProperty("--b", String(ranged ? Math.max(u[0]!, u[1]!) : u[0]!));
    track.toggleAttribute("data-disabled", !on);
    ticks.set(s, tickValues(s, rt.value(id, "ticks") as number | null));
    label.follow();
    state({ inactive: !activeOf(rt, id), held });
  };
  // A range slider's low thumb stops at the high one, and the high one at the low one.
  const kept = (k: number, v: number): number => {
    if (!ranged) return v;
    return k === 0 ? Math.min(v, valueOfTarget(1)) : Math.max(v, valueOfTarget(0));
  };
  const write = (k: number, v: number) => {
    jumpTo(rt, scheduler, part, obj, targets[k]!, kept(k, v));
    refresh();
  };
  const along = (e: PointerEvent): number => {
    const box = track.getBoundingClientRect();
    const room = box.width - 2 * THUMB_HALF;
    return room > 0 ? Math.min(Math.max((e.clientX - box.left - THUMB_HALF) / room, 0), 1) : 0;
  };
  track.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || !usable(rt, id)) return;
    const hit = thumbs.findIndex((t) => t === e.target || t.contains(e.target as Node));
    // A press on a range slider's track off its thumbs moves the nearer thumb there (the
    // author, 2026-11-26).
    const s = scale();
    const k = hit >= 0 ? hit : ranged ? pressedThumb(valueOfTarget(0), valueOfTarget(1), s.lo + along(e) * (s.hi - s.lo)) : 0;
    e.preventDefault();
    thumbs[k]!.focus();
    held = true;
    hold(
      part,
      scheduler,
      obj,
      e,
      (m) => write(k, valueAt(scale(), along(m))),
      () => {
        held = false;
        refresh();
      },
    );
  });
  thumbs.forEach((thumb, k) =>
    thumb.addEventListener("keydown", (e) => {
      const move = thumbKey(e.key);
      if (move === null || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      if (!usable(rt, id)) return;
      const s = scale();
      write(k, move === "start" ? snap(s, s.lo) : move === "end" ? snap(s, s.hi) : stepFrom(s, valueOfTarget(k), move));
    }),
  );
  refresh();
  return refresh;
}

export class MtpRangeSlider extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "range-slider");
    const obj = rt.objects[id]!;
    this.refresh = trackControl(this, rt, scheduler, id, [obj.low!, obj.high!], (state) => this.pageState(state));
  }

  protected update(): void {
    this.refresh();
  }
}

// The dial's ring, in the units of its drawing, which is 100 across with its center at 0.
const RING_R = 40;

/** The point on a dial's ring at a fraction of a turn, from the top, clockwise. */
function onRing(f: number, r = RING_R): [number, number] {
  const a = f * 2 * Math.PI;
  return [r * Math.sin(a), -r * Math.cos(a)];
}

/**
 * A dial (docs/spec/controls.md, rule slider-and-dial, and the author, 2026-11-23): the raised thumb
 * on a ring, the arc from the start filled, the value in the middle, and ticks inside the ring as
 * on a clock. One turn covers the interval of its target's modular type, from the top clockwise,
 * so turning past the end wraps. A press on the ring moves the thumb there, a drag turns it, and
 * the arrow keys step it.
 */
export class MtpDial extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "dial");
    const obj = rt.objects[id]!;
    const target = obj.target!;
    const type = targetType(rt, target);
    const wrapped = rt.constraintsOf(type).find((c) => c[0] === "wrap");
    if (!wrapped) throw new Error(`the target of the dial ${String(obj.name)} is not of a modular type`);
    const [lo, hi] = [wrapped[1] as number, wrapped[2] as number];
    const int = rt.core(type) === "int";
    const scale = (): Scale => ({ lo, hi, step: rt.value(id, "step") as number | null, int, wrap: true });

    const label = labelSpan(rt, id);
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "-50 -50 100 100");
    svg.setAttribute("aria-hidden", "true");
    const shape = (tag: string, cls: string, attrs: Record<string, string> = {}) => {
      const el = document.createElementNS(SVG_NS, tag);
      el.setAttribute("class", cls);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      return el;
    };
    const ring = shape("circle", "mtp-ring", { r: String(RING_R) });
    const arc = shape("path", "mtp-arc");
    const tickMarks = shape("g", "mtp-ticks");
    const hit = shape("circle", "mtp-ring-hit", { r: String(RING_R) });
    hit.setAttribute("data-mtp-input", "ring");
    svg.append(ring, arc, tickMarks, hit);
    const thumb = makeThumb("thumb");
    thumb.setAttribute("aria-labelledby", label.span.id);
    const value = document.createElement("span");
    value.className = "mtp-dial-value";
    value.setAttribute("aria-hidden", "true");
    const face = document.createElement("div");
    face.className = "mtp-dial-face";
    face.append(svg, value, thumb);
    const wrap = document.createElement("div");
    wrap.className = "mtp-jumper mtp-dial";
    wrap.append(label.span, face);
    this.replaceChildren(wrap);

    const now = (): number => {
      const v = rt.value(target[0], target[1]);
      return typeof v === "number" ? v : lo;
    };
    let held = false;
    let ticksShown = "";
    this.refresh = () => {
      const s = scale();
      const v = now();
      const f = fractionOf(s, v);
      const [x, y] = onRing(f);
      thumb.style.left = `${50 + x}%`;
      thumb.style.top = `${50 + y}%`;
      arc.setAttribute("d", f > 0 ? `M 0 ${-RING_R} A ${RING_R} ${RING_R} 0 ${f > 0.5 ? 1 : 0} 1 ${x} ${y}` : "");
      const text = shownNumber(rt, type, v);
      value.textContent = text;
      const on = usable(rt, id);
      setThumb(thumb, v, lo, hi, text, on);
      face.toggleAttribute("data-disabled", !on);
      const values = tickValues(s, rt.value(id, "ticks") as number | null);
      if (JSON.stringify(values) !== ticksShown) {
        ticksShown = JSON.stringify(values);
        tickMarks.replaceChildren(
          ...values.map((t) => {
            const [x1, y1] = onRing(fractionOf(s, t), RING_R - 5);
            const [x2, y2] = onRing(fractionOf(s, t), RING_R - 9);
            return shape("line", "mtp-tick", { x1: String(x1), y1: String(y1), x2: String(x2), y2: String(y2), "data-value": String(t) });
          }),
        );
      }
      label.follow();
      this.pageState({ inactive: !activeOf(rt, id), held });
    };
    const write = (v: number) => {
      jumpTo(rt, scheduler, this, obj, target, v);
      this.refresh();
    };
    const turned = (e: PointerEvent): number => {
      const box = svg.getBoundingClientRect();
      const dx = e.clientX - (box.left + box.width / 2);
      const dy = e.clientY - (box.top + box.height / 2);
      const a = Math.atan2(dx, -dy) / (2 * Math.PI);
      return a < 0 ? a + 1 : a;
    };
    face.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || !usable(rt, id)) return;
      if (e.target !== hit && e.target !== thumb && !thumb.contains(e.target as Node)) return;
      e.preventDefault();
      thumb.focus();
      held = true;
      hold(
        this,
        scheduler,
        obj,
        e,
        (m) => write(valueAt(scale(), turned(m))),
        () => {
          held = false;
          this.refresh();
        },
      );
    });
    // A ring has no ends, so Home and End do nothing on a dial.
    thumb.addEventListener("keydown", (e) => {
      const move = thumbKey(e.key);
      if (typeof move !== "number" || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      if (usable(rt, id)) write(stepFrom(scale(), now(), move));
    });
    this.refresh();
  }

  protected update(): void {
    this.refresh();
  }
}

/**
 * A number field (docs/spec/controls.md, rule number-field, and the author, 2026-11-23): its label,
 * which the reader may drag sideways to scrub, then a box with the − and + buttons and the value,
 * which the reader may type into. The arrow keys and the buttons add or subtract the step, or ten
 * steps with Shift. A typed value is written only when committed, and Escape drops it (the
 * author, 2026-11-26).
 */
export class MtpNumberField extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "number-field");
    const obj = rt.objects[id]!;
    const target = obj.target!;
    const type = targetType(rt, target);
    const buttons = Boolean(rt.value(id, "buttons"));
    const typing = Boolean(rt.value(id, "typing"));

    const label = labelSpan(rt, id);
    label.span.dataset.mtpInput = "scrub";
    label.span.classList.add("mtp-scrubber");
    const box = document.createElement("div");
    box.className = "mtp-box";
    const live = liveRegion();
    let field: HTMLElement;
    if (typing) {
      const text = document.createElement("input");
      text.type = "text";
      text.inputMode = "decimal";
      text.autocomplete = "off";
      text.spellcheck = false;
      text.dataset.mtpInput = "box";
      field = text;
    } else {
      field = document.createElement("span");
      field.className = "mtp-value";
      field.dataset.mtpInput = "value";
      // With neither buttons nor typing, the value is underlined as the sign that it can be
      // scrubbed (the author, 2026-11-23).
      if (!buttons) field.classList.add("mtp-scrub", "mtp-scrubber");
    }
    field.setAttribute("role", "spinbutton");
    field.setAttribute("aria-labelledby", label.span.id);
    const stepButton = (name: "minus" | "plus") => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `mtp-field-button mtp-${name}`;
      b.dataset.mtpInput = name;
      b.textContent = name === "minus" ? "−" : "+";
      b.setAttribute("aria-label", name === "minus" ? "decrease" : "increase");
      // The focus stays in the box, as the buttons repeat what the arrow keys do there.
      b.tabIndex = -1;
      b.addEventListener("click", (e) => stepBy((name === "minus" ? -1 : 1) * (e.shiftKey ? 10 : 1)));
      return b;
    };
    const minus = buttons ? stepButton("minus") : null;
    const plus = buttons ? stepButton("plus") : null;
    box.append(...[minus, field, plus].filter((n): n is HTMLElement => n !== null));
    const wrap = document.createElement("div");
    wrap.className = "mtp-jumper mtp-field";
    wrap.append(label.span, box, live);
    this.replaceChildren(wrap);

    const now = (): number => {
      const v = rt.value(target[0], target[1]);
      return typeof v === "number" ? v : 0;
    };
    const step = () => rt.value(id, "step") as number;
    // Whether the box holds text typed and not yet committed: it then shows that text.
    let dirty = false;
    let held = false;
    this.refresh = () => {
      const v = now();
      const text = shownNumber(rt, type, v);
      if (field instanceof HTMLInputElement) {
        if (!dirty && field.value !== text) field.value = text;
      } else field.textContent = text;
      field.setAttribute("aria-valuenow", String(v));
      field.setAttribute("aria-valuetext", text);
      const on = usable(rt, id);
      if (field instanceof HTMLInputElement) field.disabled = !on;
      else {
        field.tabIndex = on ? 0 : -1;
        if (on) field.removeAttribute("aria-disabled");
        else field.setAttribute("aria-disabled", "true");
      }
      for (const b of [minus, plus]) if (b) b.disabled = !on;
      label.follow();
      this.pageState({ inactive: !activeOf(rt, id), held });
    };
    const write = (v: number) => {
      jumpTo(rt, scheduler, this, obj, target, v);
      this.refresh();
    };
    const stepBy = (n: number) => {
      if (!usable(rt, id)) return;
      dirty = false;
      const v = now();
      write(tidy(v + n * step(), v, step()));
    };
    const commit = () => {
      if (!(field instanceof HTMLInputElement) || !dirty) return;
      const typed = field.value;
      dirty = false;
      const v = parseNumber(typed);
      if (v !== null && usable(rt, id)) jumpTo(rt, scheduler, this, obj, target, v);
      this.refresh();
      field.value = shownNumber(rt, type, now());
      if (v === null || !equal(now(), v)) refuse(box, live, `${typed.trim()} is not allowed. The value is ${field.value}.`);
    };
    field.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && field instanceof HTMLInputElement) {
        e.preventDefault();
        commit();
        return;
      }
      if (e.key === "Escape" && field instanceof HTMLInputElement) {
        if (!dirty) return;
        e.preventDefault();
        dirty = false;
        this.refresh();
        return;
      }
      // While the box holds typed text, the arrow keys move the text cursor, as in any text box
      // (the author, 2026-11-26).
      if (dirty) return;
      if ((e.key !== "ArrowUp" && e.key !== "ArrowDown") || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      stepBy((e.key === "ArrowUp" ? 1 : -1) * (e.shiftKey ? 10 : 1));
    });
    if (field instanceof HTMLInputElement) {
      field.addEventListener("input", () => (dirty = true));
      // Tab leaves the field, so it commits too.
      field.addEventListener("blur", commit);
    }
    const scrub = (e: PointerEvent) => {
      if (e.button !== 0 || !usable(rt, id)) return;
      e.preventDefault();
      commit();
      const x0 = e.clientX;
      const v0 = now();
      let last = 0;
      held = true;
      hold(
        this,
        scheduler,
        obj,
        e,
        (m) => {
          const n = Math.trunc((m.clientX - x0) / SCRUB_PX) * (m.shiftKey ? 10 : 1);
          if (n === last) return;
          last = n;
          write(tidy(v0 + n * step(), v0, step()));
        },
        () => {
          held = false;
          this.refresh();
        },
      );
    };
    label.span.addEventListener("pointerdown", scrub);
    if (field.classList.contains("mtp-scrub")) field.addEventListener("pointerdown", scrub);
    this.refresh();
  }

  protected update(): void {
    this.refresh();
  }
}

/**
 * A text field (docs/spec/controls.md, rule text-field): its label above a box, in the number
 * field's style. A typed string is written only when committed, and one that breaks the target's
 * conditions is not written. Escape drops the typed string (the author, 2026-11-26).
 */
export class MtpTextField extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "text-field");
    const obj = rt.objects[id]!;
    const target = obj.target!;
    const label = labelSpan(rt, id);
    const box = document.createElement("div");
    box.className = "mtp-box";
    const field = document.createElement("input");
    field.type = "text";
    field.autocomplete = "off";
    field.dataset.mtpInput = "box";
    field.setAttribute("aria-labelledby", label.span.id);
    box.append(field);
    const live = liveRegion();
    const wrap = document.createElement("div");
    wrap.className = "mtp-jumper mtp-field mtp-text";
    wrap.append(label.span, box, live);
    this.replaceChildren(wrap);

    const now = () => String(rt.value(target[0], target[1]) ?? "");
    let dirty = false;
    this.refresh = () => {
      if (!dirty && field.value !== now()) field.value = now();
      field.disabled = !usable(rt, id);
      label.follow();
      this.pageState({ inactive: !activeOf(rt, id) });
    };
    const commit = () => {
      if (!dirty) return;
      const typed = field.value;
      dirty = false;
      if (usable(rt, id)) jumpTo(rt, scheduler, this, obj, target, typed);
      field.value = now();
      this.refresh();
      if (now() !== typed) refuse(box, live, `“${typed}” is not allowed.`);
    };
    field.addEventListener("input", () => (dirty = true));
    field.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        commit();
      } else if (e.key === "Escape" && dirty) {
        e.preventDefault();
        dirty = false;
        this.refresh();
      }
    });
    field.addEventListener("blur", commit);
    this.refresh();
  }

  protected update(): void {
    this.refresh();
  }
}

/** An option of a select, with what it is shown as: its label, or its value. */
interface Choice {
  value: () => unknown;
  text: () => { node: Node; follow: () => void };
}

function choicesOf(rt: Runtime, obj: Obj): Choice[] {
  return (obj.options ?? []).map((o) => {
    const value = () => rt.evaluate(o.value);
    const label = o.label;
    const shown = label ? () => String(rt.evaluate(label)) : () => show(value(), rt.core(o.value.type), "");
    return { value, text: () => textPart(shown, Boolean(label && o["label-tex"])) };
  });
}

/**
 * A select or a multi-select (docs/spec/controls.md, rules select-options, select-kinds and
 * multi-select). Choosing an option writes at once: a select writes the option, and a multi-select
 * the list with the option added or removed, in the options' order. A target that holds no
 * option's value shows no option chosen. Gives what brings it up to date.
 */
function choiceControl(part: HTMLElement, rt: Runtime, scheduler: Scheduler, id: number, many: boolean, state: PageState): () => void {
  const obj = rt.objects[id]!;
  const target = obj.target!;
  const choices = choicesOf(rt, obj);
  const label = labelSpan(rt, id);
  const wrap = document.createElement("div");
  wrap.className = "mtp-jumper mtp-choice";
  wrap.append(label.span);
  part.replaceChildren(wrap);

  const list = (): unknown[] => {
    const v = rt.value(target[0], target[1]);
    return Array.isArray(v) ? v : [];
  };
  const chosen = (): boolean[] => {
    const values = choices.map((c) => c.value());
    if (many) return chosenIn(list(), values);
    const now = rt.value(target[0], target[1]);
    const at = values.findIndex((v) => equal(v, now));
    return values.map((_, i) => i === at);
  };
  const choose = (i: number) => {
    if (!usable(rt, id)) return;
    const v = many ? toggledList(list(), choices.map((c) => c.value()), i) : choices[i]!.value();
    jumpTo(rt, scheduler, part, obj, target, v);
    refresh();
  };
  const follows: (() => void)[] = [label.follow];
  const as = obj.as ?? "menu";
  let paint: (on: boolean, picked: boolean[]) => void;

  if (as === "menu") {
    const menu = document.createElement("div");
    menu.className = "mtp-menu";
    const button = document.createElement("button");
    button.type = "button";
    button.id = partId();
    button.className = "mtp-menu-button";
    button.dataset.mtpInput = "menu";
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-labelledby", `${label.span.id} ${button.id}`);
    const shownText = document.createElement("span");
    shownText.className = "mtp-menu-text";
    button.append(shownText);
    // With nothing chosen, the button shows the control's label (the author, 2026-11-26). A screen
    // reader already reads the label as the button's name, so it does not read this one.
    const placeholder = document.createElement("span");
    placeholder.className = "mtp-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    const placeholderText = labelPart(rt, id);
    follows.push(placeholderText.follow);
    placeholder.append(placeholderText.node);
    button.insertAdjacentHTML("beforeend", CHEVRON_ICON);
    const box = document.createElement("div");
    box.id = partId();
    box.className = "mtp-listbox";
    box.setAttribute("role", "listbox");
    box.setAttribute("aria-labelledby", label.span.id);
    box.tabIndex = -1;
    box.hidden = true;
    if (many) box.setAttribute("aria-multiselectable", "true");
    button.setAttribute("aria-controls", box.id);
    // The text of each option in the list, and a second one that the button shows when it is chosen.
    const inButton = choices.map((c) => {
      const t = c.text();
      follows.push(t.follow);
      const span = document.createElement("span");
      span.className = "mtp-menu-item";
      span.append(t.node);
      return span;
    });
    const options = choices.map((c, i) => {
      const t = c.text();
      follows.push(t.follow);
      const o = document.createElement("div");
      o.id = `${box.id}-${i + 1}`;
      o.className = "mtp-option";
      o.setAttribute("role", "option");
      o.dataset.mtpInput = `option-${i + 1}`;
      o.append(t.node);
      o.addEventListener("click", () => pick(i));
      return o;
    });
    box.append(...options);
    menu.append(button, box);
    wrap.append(menu);
    let active = 0;
    const activate = (i: number) => {
      active = Math.min(Math.max(i, 0), options.length - 1);
      options.forEach((o, j) => o.classList.toggle("mtp-active", j === active));
      box.setAttribute("aria-activedescendant", options[active]!.id);
    };
    const outside = (e: Event) => {
      if (!menu.contains(e.target as Node)) close(false);
    };
    const open = () => {
      if (!usable(rt, id)) return;
      box.hidden = false;
      button.setAttribute("aria-expanded", "true");
      const at = chosen().indexOf(true);
      activate(at < 0 ? 0 : at);
      box.focus();
      document.addEventListener("pointerdown", outside, true);
    };
    const close = (refocus: boolean) => {
      if (box.hidden) return;
      box.hidden = true;
      button.setAttribute("aria-expanded", "false");
      document.removeEventListener("pointerdown", outside, true);
      if (refocus) button.focus();
    };
    // A select closes once an option is chosen. A multi-select stays open, since the reader may
    // choose several.
    const pick = (i: number) => {
      activate(i);
      choose(i);
      if (!many) close(true);
    };
    button.addEventListener("click", () => (box.hidden ? open() : close(true)));
    button.addEventListener("keydown", (e) => {
      if (!["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) return;
      e.preventDefault();
      open();
    });
    box.addEventListener("keydown", (e) => {
      const moves: Record<string, number> = { ArrowDown: active + 1, ArrowUp: active - 1, Home: 0, End: options.length - 1 };
      if (e.key in moves) {
        e.preventDefault();
        activate(moves[e.key]!);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        pick(active);
      } else if (e.key === "Escape") {
        e.preventDefault();
        close(true);
      } else if (e.key === "Tab") close(false);
    });
    paint = (on, picked) => {
      button.disabled = !on;
      if (!on) close(false);
      options.forEach((o, i) => o.setAttribute("aria-selected", String(picked[i])));
      const parts: Node[] = [];
      inButton.forEach((span, i) => {
        if (!picked[i]) return;
        if (parts.length) parts.push(document.createTextNode(", "));
        parts.push(span);
      });
      shownText.replaceChildren(...(parts.length ? parts : [placeholder]));
    };
  } else if (as === "buttons") {
    const row = document.createElement("div");
    row.className = "mtp-segments";
    row.setAttribute("role", many ? "group" : "radiogroup");
    row.setAttribute("aria-labelledby", label.span.id);
    const segments = choices.map((c, i) => {
      const t = c.text();
      follows.push(t.follow);
      const b = document.createElement("button");
      b.type = "button";
      b.className = "mtp-segment";
      b.dataset.mtpInput = `option-${i + 1}`;
      if (!many) b.setAttribute("role", "radio");
      b.append(t.node);
      b.addEventListener("click", () => choose(i));
      return b;
    });
    // In a radio group the arrow keys move to the next option and choose it, and Tab reaches
    // only the chosen one, as the ARIA radio group pattern has it.
    if (!many)
      segments.forEach((b, i) =>
        b.addEventListener("keydown", (e) => {
          const by = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
          if (!by) return;
          e.preventDefault();
          const j = (i + by + segments.length) % segments.length;
          segments[j]!.focus();
          choose(j);
        }),
      );
    row.append(...segments);
    wrap.append(row);
    paint = (on, picked) => {
      const first = picked.indexOf(true);
      segments.forEach((b, i) => {
        b.disabled = !on;
        if (many) b.setAttribute("aria-pressed", String(picked[i]));
        else {
          b.setAttribute("aria-checked", String(picked[i]));
          b.tabIndex = i === (first < 0 ? 0 : first) ? 0 : -1;
        }
      });
    };
  } else {
    // 'radio' for a select, 'checkbox' for a multi-select: one native input per line.
    const group = document.createElement("div");
    group.className = "mtp-marks";
    group.setAttribute("role", many ? "group" : "radiogroup");
    group.setAttribute("aria-labelledby", label.span.id);
    const name = partId();
    const marks = choices.map((c, i) => {
      const t = c.text();
      follows.push(t.follow);
      const line = document.createElement("label");
      line.className = "mtp-mark";
      const mark = document.createElement("input");
      mark.type = many ? "checkbox" : "radio";
      mark.name = name;
      mark.dataset.mtpInput = `option-${i + 1}`;
      mark.addEventListener("change", () => choose(i));
      const text = document.createElement("span");
      text.append(t.node);
      line.append(mark, text);
      group.append(line);
      return mark;
    });
    wrap.append(group);
    paint = (on, picked) => {
      marks.forEach((m, i) => {
        m.disabled = !on;
        m.checked = picked[i]!;
      });
    };
  }

  const refresh = () => {
    for (const f of follows) f();
    paint(usable(rt, id), chosen());
    state({ inactive: !activeOf(rt, id) });
  };
  refresh();
  return refresh;
}

// The menu button's mark (Tabler's chevron-down), drawn as the stepper's chevrons are.
const CHEVRON_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6l6 -6"/></svg>';

export class MtpSelect extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "select");
    this.refresh = choiceControl(this, rt, scheduler, id, false, (state) => this.pageState(state));
  }

  protected update(): void {
    this.refresh();
  }
}

export class MtpMultiSelect extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "multi-select");
    this.refresh = choiceControl(this, rt, scheduler, id, true, (state) => this.pageState(state));
  }

  protected update(): void {
    this.refresh();
  }
}

const ELEMENTS: [string, CustomElementConstructor][] = [
  ["mtp-model", MtpModel],
  ["mtp-canvas", MtpCanvas],
  ["mtp-readout", MtpReadout],
  ["mtp-display", MtpDisplay],
  ["mtp-slider", MtpSlider],
  ["mtp-button", MtpButton],
  ["mtp-play", MtpPlay],
  ["mtp-stepper", MtpStepper],
  ["mtp-toggle", MtpToggle],
  ["mtp-range-slider", MtpRangeSlider],
  ["mtp-dial", MtpDial],
  ["mtp-number-field", MtpNumberField],
  ["mtp-text-field", MtpTextField],
  ["mtp-select", MtpSelect],
  ["mtp-multi-select", MtpMultiSelect],
];

export function define(): void {
  if (typeof document !== "undefined" && !document.getElementById("mtp-controls")) {
    const style = document.createElement("style");
    style.id = "mtp-controls";
    style.textContent = CONTROLS_CSS;
    document.head.append(style);
  }
  for (const [tag, element] of ELEMENTS) {
    if (!customElements.get(tag)) customElements.define(tag, element);
  }
}

// The nearest shape that is a or b or holds them both, or null when none does.
function holding(rt: Runtime, a: number, b: number): number | null {
  const around = new Set<number>();
  for (let i: number | null = a; i !== null; i = rt.parent(i)) around.add(i);
  for (let i: number | null = b; i !== null; i = rt.parent(i)) if (around.has(i)) return i;
  return null;
}
