// The page elements (docs/data-model.md, "On the page"): <mtp-model> holds a figure's .mtpc and
// its runtime, and views and controls placed anywhere in the page find it by id, so an author can
// put each one where it fits. Every writer emits writes to the model; views redraw on each change.
import { CONTROLS_CSS } from "./controls-style.ts";
import { placeTicks } from "./ticks.ts";
import { Scheduler } from "./animate.ts";
import { apply, invert } from "./builtins.ts";
import { Listeners, heardIn, holds } from "./click.ts";
import { type Doc, FORMAT_VERSION, type Obj, itemsOf } from "./doc.ts";
import { Drags } from "./drag.ts";
import { latexOf, termClass, typeset } from "./math.ts";
import { Player } from "./player.ts";
import { Pointer } from "./pointer.ts";
import { Runtime } from "./runtime.ts";
import { DrawMemo, type Look, draw, elementsMade, lookBox, shapesOf, viewOf, zoom } from "./svg.ts";
import { type Ease, applyEase } from "./transitions.ts";

export { FORMAT_VERSION };
const READY = "mtp-ready";
const CHANGE = "mtp-change";
// A view went live or back to quiet (mtp-16z).
const MODE = "mtp-mode";
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

/** How the page asks for animation frames; tests replace it to move time by hand. */
export const frames = {
  request: (callback: (ms: number) => void): void => {
    requestAnimationFrame(callback);
  },
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
  // The views and controls that have come into view, and what waits for one to.
  private seen = new Set<number>();
  private waiting = new Map<number, (() => void)[]>();
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
    if (doc.mtpc !== FORMAT_VERSION) {
      this.fail(`this runtime reads .mtpc version ${FORMAT_VERSION}, but the figure is version ${String(doc.mtpc)}`);
      return;
    }
    const rt = new Runtime(doc);
    this.runtime = rt;
    this.scheduler = new Scheduler(
      () => this.changed(),
      () => this.wake(),
    );
    this.drags = new Drags(rt);
    this.clicks = new Listeners(rt, "on-click");
    this.releases = new Listeners(rt, "on-release");
    this.dragstarts = new Listeners(rt, "on-dragstart");
    this.dragends = new Listeners(rt, "on-dragend");
    this.error = null;
    this.seen.clear();
    this.waiting.clear();
    rt.onChange(() => this.changed());
    const scheduler = this.scheduler;
    rt.objects.forEach((o, i) => {
      if (o.kind !== "on-view") return;
      this.whenSeen(o.view!, () => {
        const player = activeOf(rt, i) ? playerFor(rt, o) : null;
        if (player) scheduler.start(player, o);
      });
    });
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }

  /** Makes a view with a quiet mode live, or quiet again (docs/reference.md, "Quiet and live
   * views"), playing its active on-live or on-quiet listeners. */
  setLive(view: number, live: boolean): void {
    const rt = this.runtime;
    const scheduler = this.scheduler;
    if (!rt || !scheduler || !rt.quietMode.has(view) || rt.quiet.has(view) !== live) return;
    if (live) rt.quiet.delete(view);
    else rt.quiet.add(view);
    const kind = live ? "on-live" : "on-quiet";
    rt.objects.forEach((o, i) => {
      if (o.kind !== kind || o.view !== view || !activeOf(rt, i)) return;
      const player = playerFor(rt, o);
      if (player) scheduler.start(player, o);
    });
    this.dispatchEvent(new Event(MODE, { bubbles: true }));
    this.changed();
  }

  /** Runs work the first time the view or control id comes into view, or now if it has. */
  whenSeen(id: number, work: () => void): void {
    if (this.seen.has(id)) work();
    else this.waiting.set(id, [...(this.waiting.get(id) ?? []), work]);
  }

  /** Called by a view or control when it comes into view; only the first time counts. */
  markSeen(id: number): void {
    if (this.seen.has(id)) return;
    this.seen.add(id);
    for (const work of this.waiting.get(id) ?? []) work();
    this.waiting.delete(id);
  }

  /** Tells every view and control of this model to show the current values. */
  changed(): void {
    this.scheduler?.told();
    this.dispatchEvent(new Event(CHANGE, { bubbles: true }));
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
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }
}

// What views and controls share: finding their model and their object, and hearing when the
// model loads or changes.
abstract class MtpPart extends HTMLElement {
  private onReady = (event: Event) => {
    if (this.mine(event)) this.build();
  };
  private onChange = (event: Event) => {
    if (this.mine(event)) this.guard(() => this.update());
  };
  private onMode = (event: Event) => {
    if (this.mine(event)) this.moded(false);
  };

  connectedCallback(): void {
    document.addEventListener(READY, this.onReady);
    document.addEventListener(CHANGE, this.onChange);
    document.addEventListener(MODE, this.onMode);
    this.addEventListener("keydown", this.onKey);
    const model = this.model();
    if (model && (model.runtime || model.error)) this.build();
  }

  disconnectedCallback(): void {
    document.removeEventListener(READY, this.onReady);
    document.removeEventListener(CHANGE, this.onChange);
    document.removeEventListener(MODE, this.onMode);
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
        this.watch(model);
      }
    });
  }

  // Tells the model when this element first comes into view (on-view, autoplay). On screen is not
  // enough: a page may hide its content at opacity 0 while it loads, so the element counts as in
  // view only once no ancestor is fully transparent or hidden, checked again each frame meanwhile.
  private watch(model: MtpModel): void {
    const id = this.shown;
    if (id === null || typeof IntersectionObserver === "undefined") return;
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
      model.markSeen(id);
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
  private folding: Animation | null = null;
  private folded: boolean | null = null;
  private onKey = (event: KeyboardEvent) => {
    const rt = this.model()?.runtime;
    const id = this.shown;
    if (event.key === "Escape" && rt && id !== null && rt.quietMode.has(id) && !rt.quiet.has(id)) this.model()!.setLive(id, false);
  };

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
      this.dataset.mtpMode = quiet ? "quiet" : "live";
      if (!this.switch) {
        this.switch = makeSwitch(this, () => model.setLive(id, rt.quiet.has(id)));
        this.append(this.switch);
      }
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
// The switch's icons: a hand, to make a view live, as in the Bourgain paper's figures, and a
// cross to put it back to quiet.
const HAND_ICON =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 11V6a2 2 0 0 0-4 0"/><path d="M14 10V4a2 2 0 0 0-4 0v2"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/></svg>';
const CLOSE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';

/** A view's switch: one button that makes it live and, pressed again, quiet, so the keyboard's
 * focus stays on it. A readout and a formula inside a paragraph take it in the line. */
function makeSwitch(view: HTMLElement, press: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "mtp-switch";
  if (view.localName === "mtp-readout" || view.style.display === "inline") button.classList.add("mtp-switch-inline");
  button.addEventListener("click", press);
  return button;
}

function playerFor(rt: Runtime, writer: Obj): Player | null {
  return writer.animation === null || writer.animation === undefined
    ? null
    : new Player(rt, writer.animation, writer.conditions ?? [], writer.rest ?? 0);
}

export class MtpCanvas extends MtpPart {
  private redraw: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const canvas = this.find(rt, "canvas");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    const drags = model.drags!;
    const clicks = model.clicks!;
    const releases = model.releases!;
    const dragstarts = model.dragstarts!;
    const dragends = model.dragends!;
    const toggles = new Toggles(rt, canvas, scheduler, () => this.redraw());
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
    this.redraw = () => {
      toggles.follow();
      const quiet = rt.quiet.has(canvas);
      // Back to quiet, the reader can no longer undo a pan or zoom, so the canvas drops it.
      if (quiet && !wasQuiet) Object.assign(look, { scale: 1, dx: 0, dy: 0 });
      wasQuiet = quiet;
      // Elsewhere a finger on the canvas scrolls the page.
      const action = allows("pan") || allows("zoom") || pointer.onCanvas ? "none" : "";
      if (svg.style.touchAction !== action) svg.style.touchAction = action;
      draw(rt, canvas, svg, (k) => toggles.shownBy(k), look, memo);
      const made = elementsMade();
      if (rt.clock !== shownAt || made !== madeAt) {
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
    const toUser = (event: { clientX: number; clientY: number }): [number, number] => {
      const ctm = svg.getScreenCTM?.();
      const at: [number, number] = [event.clientX, event.clientY];
      if (!ctm) return at;
      return apply(invert([ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f]), at) as [number, number];
    };
    const toScene = (event: PointerEvent): [number, number] =>
      apply(invert(viewOf(rt, canvas).toUser), toUser(event)) as [number, number];
    // The reader zooms between the canvas's bounds. Zoomed in, what is shown stays inside the
    // view box, so the reader never sees past what the author framed (the author, 2026-11-04);
    // zoomed out past it, the view box stays inside what is shown (the author, 2026-11-08).
    const inside = () => {
      const [, , w, h] = viewOf(rt, canvas).box as [number, number, number, number];
      const [mx, my] = [Math.abs(w - w / look.scale) / 2, Math.abs(h - h / look.scale) / 2];
      look.dx = Math.min(Math.max(look.dx, -mx), mx);
      look.dy = Math.min(Math.max(look.dy, -my), my);
    };
    const zoomAbout = (at: [number, number], by: number) => {
      const [x, y, w, h] = viewOf(rt, canvas).box as [number, number, number, number];
      const [cx, cy] = [x + w / 2, y + h / 2];
      const [lo, hi] = [rt.value(canvas, "zoom-min") as number, rt.value(canvas, "zoom-max") as number];
      const factor = Math.min(Math.max(look.scale * by, lo), hi) / look.scale;
      // The point under the pointer stays where it is.
      look.dx = at[0] + (cx + look.dx - at[0]) / factor - cx;
      look.dy = at[1] + (cy + look.dy - at[1]) / factor - cy;
      look.scale *= factor;
      inside();
      zoom(rt, canvas, svg, look);
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
      zoom(rt, canvas, svg, look);
    });
    // The pointers pressed where nothing is dragged, and where each is: one pans, two pinch.
    const touches = new Map<number, [number, number]>();
    const unitsPerPx = () =>
      lookBox(viewOf(rt, canvas).box, look)[2]! / (svg.getBoundingClientRect?.().width || 640);
    const spread = () => {
      const [a, b] = [...touches.values()] as [[number, number], [number, number]];
      return { gap: Math.hypot(a[0] - b[0], a[1] - b[1]), mid: { clientX: (a[0] + b[0]) / 2, clientY: (a[1] + b[1]) / 2 } };
    };
    // The shape pressed, for the click on release; drawing replaces the elements, so shapes are
    // compared by id.
    let pressed: number | null = null;
    // Where a finger came down, to tell a tap from a drag: a finger is never quite still.
    let press: { id: number; x: number; y: number; at: [number, number]; moved: boolean } | null = null;
    const play = (listeners: (Obj | null)[]) => {
      for (const listener of listeners) {
        const player = listener ? playerFor(rt, listener) : null;
        if (listener && player) scheduler.start(player, listener);
      }
    };
    // on-enter, on-leave and on-pointermove. A finger has no hover, so a tap enters a shape and
    // it stays entered until the reader presses elsewhere, here or anywhere on the page.
    const follow = (event: PointerEvent, hit: number | null) => {
      play(pointer.onto(hit));
      pointer.move(toScene(event), (targets, source) => scheduler.claim(targets, source));
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
      const touch = touchy(event);
      pressed = touch ? targetOf(event) : hitOf(event);
      held = touch && pressed !== null && reaches(pressed);
      if (held && event.target !== svg) (event.target as Element).addEventListener("touchstart", hold, { passive: false, once: true });
      follow(event, pressed);
      if (touch && event.isPrimary) {
        press = { id: event.pointerId, x: event.clientX, y: event.clientY, at: toScene(event), moved: false };
      }
      if (pressed !== null && drags.grab(pressed, toScene(event), canvas)) {
        scheduler.claim(drags.targets, drags);
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
        // As JS's dragstart, a drag starts at its first move, and its listeners play before the
        // drag writes, so they may reset what the drag then reads (mtp-5opl).
        if (!drags.moved) play(dragstarts.find(drags.shape!, canvas));
        drags.move(toScene(event));
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
        svg.setAttribute("viewBox", lookBox(viewOf(rt, canvas).box, look).join(" "));
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
      scheduler.claim(drags.targets, drags);
      play(dragstarts.find(drags.shape!, canvas));
      drags.move(toScene(event));
      drags.release();
      return chosen.shape;
    };
    svg.addEventListener("pointerup", (event) => {
      lift(event);
      const touch = touchy(event);
      // As JS's dragend, only a drag that moved ends.
      const ended = drags.moved ? drags.shape : null;
      const grabbed = drags.shape;
      drags.release();
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
// its toggle-ease. Turning back midway covers only what is left, at the same speed.
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
    const same = wanted.size === this.wanted.size && [...wanted].every((key) => this.wanted.has(key));
    // Leaving shapes keep their place after the ones the item gives now, until they are gone.
    this.order = now.map((ids, k) => [...ids, ...(this.order[k] ?? []).filter((id) => !ids.includes(id))]);
    if (same) return;
    this.wanted = wanted;
    for (const key of wanted) if (!this.levels.has(key)) this.levels.set(key, 0);
    if (this.duration <= 0) {
      this.levels = new Map([...wanted].map((key) => [key, 1]));
      return;
    }
    if (this.moving) return;
    this.moving = true;
    this.scheduler.addTicker((seconds) => {
      const step = seconds / this.duration;
      this.moving = false;
      for (const [key, level] of this.levels) {
        const next = this.wanted.has(key) ? Math.min(level + step, 1) : Math.max(level - step, 0);
        if (next <= 0 && !this.wanted.has(key)) this.levels.delete(key);
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
      rt.objects.filter((o) => o.kind === kind && o.shape === id && heardIn(o, display, rt.quiet) && holds(rt, o.active));
    const play = (listeners: Obj[]) => {
      for (const listener of listeners) {
        const player = playerFor(rt, listener);
        if (player) scheduler.start(player, listener);
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
    const player = playerFor(rt, rt.objects[id]!);
    const input = document.createElement("input");
    input.type = "range";
    const stops = rt.objects[id]!.attrs?.step ? (rt.value(id, "step") as number) : null;
    // With (step n) the knob stops at n evenly spaced stops.
    input.min = "0";
    input.max = stops === null ? "1000" : String(stops - 1);
    input.step = "1";
    input.value = String(Math.round((rt.value(id, "position") as number) * Number(input.max)));
    // How far along the knob is, which fills the track up to it.
    const fill = () => input.style.setProperty("--u", String(Number(input.value) / Number(input.max)));
    fill();
    input.addEventListener("input", () => {
      if (!activeOf(rt, id)) return;
      fill();
      const u = Number(input.value) / Number(input.max);
      if (player) {
        scheduler.claim(player.targets, this);
        player.scrub(u);
      }
      rt.write(id, "position", u);
    });
    input.addEventListener("change", () => player?.release());
    // A slider follows its target: when another writer changes the one variable or attribute its animation
    // moves, the knob goes to the position whose value is closest (reference.md, "Controls").
    let scrubbing = false;
    input.addEventListener("pointerdown", () => {
      scrubbing = true;
    });
    input.addEventListener("pointerup", () => {
      scrubbing = false;
    });
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
    this.gate = () => {
      input.disabled = !activeOf(rt, id);
    };
    this.gate();
    // The label follows what it is given, as anything bound does.
    const text = document.createTextNode(labelOf(rt, id));
    this.named = () => {
      text.data = labelOf(rt, id);
    };
    // The label sits above the track: a label whose width changes as it follows its value would
    // otherwise move the track under the pointer while it drags.
    const label = document.createElement("label");
    label.append(text, input);
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
    button.textContent = labelOf(rt, id);
    // A press plays the animation from the start; a press while it runs starts it again.
    button.addEventListener("click", () => {
      if (!activeOf(rt, id)) return;
      const player = playerFor(rt, rt.objects[id]!);
      if (player) scheduler.start(player, this);
    });
    // Only a button given (selected bool) says whether it is the current choice; any other is
    // not a toggle button, and says nothing.
    const chooses = rt.objects[id]!.attrs?.selected !== undefined;
    this.gate = () => {
      button.disabled = !activeOf(rt, id);
      button.textContent = labelOf(rt, id);
      if (chooses) button.setAttribute("aria-pressed", String(Boolean(rt.value(id, "selected"))));
    };
    this.gate();
    this.replaceChildren(button);
  }

  protected update(): void {
    this.gate();
  }
}

// The play button's icons, drawn in the color of the page on the button's ink.
const PLAY_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.2v9.6a.6.6 0 0 0 .9.5l7.6-4.8a.6.6 0 0 0 0-1L5.9 2.7a.6.6 0 0 0-.9.5z"/></svg>';
const PAUSE_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="3" width="3" height="10" rx="0.8"/><rect x="9.5" y="3" width="3" height="10" rx="0.8"/></svg>';
// How far, in CSS pixels, a mouse may move on the bars and still tap one rather than drag.
const MOUSE_SLOP = 3;
// How far past a stop, in seconds, the left arrow still goes back to the stop before it rather
// than to that one, so pressing it twice while the play runs goes back two.
const BACK_GRACE = 0.5;

// Whether keys pressed on el are its own: a field takes Space and the arrows, and so does any
// other control.
function takesKeys(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return el.isContentEditable || el.closest("input, textarea, select, button, [role=slider], mtp-slider, mtp-toggle, mtp-button") !== null;
}

/**
 * A play (docs/reference.md, "Controls"; mtp-33xt): a play button, then one bar per step, each
 * as wide as its step's duration and filling as it plays, and the step now playing under them.
 * The reader drags along the bars to scrub the tour, and taps one to jump to its step's start.
 */
export class MtpPlay extends MtpPart {
  private refresh: () => void = () => {};
  private onPage: ((event: KeyboardEvent) => void) | null = null;

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = null;
  }

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "play");
    const obj = rt.objects[id]!;
    // The one player the bars show. It is kept after the tour ends or another writer cancels it,
    // so the bars stay where it stood; a press after the end starts a new one.
    let player: Player | null = null;
    const layout = playerFor(rt, obj);
    if (!layout) {
      this.replaceChildren();
      return;
    }
    const split = Boolean(rt.value(id, "buttons"));
    const all = layout.spans;
    const spans = split ? all : [{ start: all[0]!.start, end: all.at(-1)!.end }];
    const names = (obj.animation !== null && obj.animation !== undefined ? rt.objects[obj.animation]!.names : undefined) ?? [];

    const play = document.createElement("button");
    play.type = "button";
    play.className = "mtp-play-button";
    const track = document.createElement("div");
    track.className = "mtp-bars";
    track.tabIndex = 0;
    track.setAttribute("role", "slider");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", String(spans.length));
    const bars = spans.map((s) => {
      const bar = document.createElement("span");
      bar.className = "mtp-bar";
      // A step that takes no time still gets a sliver, so it can be seen and tapped.
      bar.style.flexGrow = String(Math.max(s.end - s.start, 0.05 * (all.at(-1)!.end || 1)));
      bar.style.setProperty("--u", "0");
      track.append(bar);
      return bar;
    });
    const line = document.createElement("div");
    line.className = "mtp-now";
    const indicator = document.createElement("div");
    indicator.className = "mtp-indicator";
    indicator.append(track);
    if (split) indicator.append(line);

    const own = (): Player => {
      const held = scheduler.playerOf(this);
      if (held) return held;
      player ??= playerFor(rt, obj)!;
      scheduler.hold(player, this);
      return player;
    };
    const seek = (t: number) => {
      own();
      scheduler.seek(this, t);
      this.refresh();
    };
    const toggle = () => {
      if (!activeOf(rt, id)) return;
      if (scheduler.running(this)) scheduler.pause(this);
      else if (player && !player.done && scheduler.playerOf(this) === player) scheduler.resume(this);
      else {
        player = playerFor(rt, obj);
        if (player) scheduler.start(player, this);
      }
      this.refresh();
    };
    play.addEventListener("click", toggle);

    // Keys (mtp-yhau): Space plays and pauses; the arrows go to the next stop or back one. The
    // stops are the starts of the steps and the end, so a rest is skipped.
    const stops = [...spans.map((s) => s.start), spans.at(-1)!.end];
    const next = () => {
      const t = player ? player.position : -1;
      const s = stops.find((x) => x > t + 1e-6);
      if (s !== undefined) seek(s);
    };
    const back = () => {
      const t = player ? player.position : 0;
      seek(stops.filter((x) => x < t - BACK_GRACE).at(-1) ?? 0);
    };
    const keys: Record<string, () => void> = { " ": toggle, ArrowRight: next, ArrowLeft: back };
    const onKey = (event: KeyboardEvent) => {
      const act = keys[event.key];
      if (!act || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      if (!event.repeat && activeOf(rt, id)) act();
    };
    this.addEventListener("keydown", (event) => {
      // The play button presses itself on Space, as any button does.
      if (event.key === " " && event.target === play) return;
      onKey(event);
    });
    // On a page with one play, as when recording it, the keys work from anywhere on the page,
    // unless what has focus takes keys of its own.
    if (this.onPage) document.removeEventListener("keydown", this.onPage);
    this.onPage = (event) => {
      if (this.contains(event.target as Node) || document.querySelectorAll("mtp-play").length !== 1) return;
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
    let press: { x: number; slop: number; playing: boolean; moved: boolean } | null = null;
    track.addEventListener("pointerdown", (event) => {
      if (!activeOf(rt, id) || event.button !== 0) return;
      const playing = scheduler.running(this);
      if (playing) scheduler.pause(this);
      press = { x: event.clientX, slop: event.pointerType === "mouse" ? MOUSE_SLOP : TOUCH_SLOP, playing, moved: false };
      track.setPointerCapture?.(event.pointerId);
      track.classList.add("mtp-dragging");
      event.preventDefault();
    });
    track.addEventListener("pointermove", (event) => {
      if (!press) return;
      if (!press.moved && Math.abs(event.clientX - press.x) <= press.slop) return;
      press.moved = true;
      seek(timeAt(event.clientX));
    });
    const release = (event: PointerEvent, tap: boolean) => {
      if (!press) return;
      const { moved, playing } = press;
      press = null;
      track.classList.remove("mtp-dragging");
      if (tap && !moved) seek(spans[nearest(event.clientX)]!.start);
      else if (moved) seek(timeAt(event.clientX));
      if (playing) scheduler.resume(this);
      this.refresh();
    };
    track.addEventListener("pointerup", (event) => release(event, true));
    track.addEventListener("pointercancel", (event) => release(event, false));

    // The step at t: the last one started by then, so a rest after a step still shows it.
    const stepAt = (t: number): number => {
      let k = 0;
      spans.forEach((s, j) => {
        if (t >= s.start - 1e-9 * Math.max(1, s.start)) k = j;
      });
      return k;
    };
    this.refresh = () => {
      const running = scheduler.running(this);
      const active = activeOf(rt, id);
      const t = player ? player.position : 0;
      play.innerHTML = running ? PAUSE_ICON : PLAY_ICON;
      play.setAttribute("aria-label", running ? "pause" : labelOf(rt, id));
      play.disabled = !active;
      track.setAttribute("aria-disabled", String(!active));
      this.toggleAttribute("data-playing", running);
      bars.forEach((bar, j) => {
        const s = spans[j]!;
        const u = s.end > s.start ? Math.min(Math.max((t - s.start) / (s.end - s.start), 0), 1) : t >= s.start && player ? 1 : 0;
        bar.style.setProperty("--u", String(Number(u.toFixed(4))));
      });
      const n = spans.length;
      const k = stepAt(t);
      const name = names[k] ?? null;
      const text = player ? `${k + 1} / ${n}${name ? ` · ${name}` : ""}` : `${n} ${n === 1 ? "step" : "steps"}`;
      line.textContent = text;
      track.setAttribute("aria-label", labelOf(rt, id));
      track.setAttribute("aria-valuenow", String(player ? k + 1 : 0));
      track.setAttribute("aria-valuetext", text);
      if (rt.value(id, "playing") !== running) rt.write(id, "playing", running);
      if (player && split && rt.value(id, "step") !== k) rt.write(id, "step", k);
    };
    this.refresh();
    this.replaceChildren(play, indicator);
    // (autoplay) starts it when the page loads; (autoplay x) the first time x comes into view.
    const start = () => {
      if (!activeOf(rt, id) || scheduler.running(this)) return;
      player = playerFor(rt, obj);
      if (player) scheduler.start(player, this);
      this.refresh();
    };
    const auto = obj.autoplay;
    if (auto === "load") start();
    else if (typeof auto === "number") model.whenSeen(auto, start);
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
    const target = rt.objects[id]!.target ?? null;
    const input = document.createElement("input");
    input.type = "checkbox";
    const members = target && rt.objects[target[0]]!.kind === "group" ? rt.objects[target[0]]!.members! : null;
    this.show = () => {
      input.disabled = !activeOf(rt, id);
      if (members && target) {
        const values = members.map((m) => Boolean(rt.value(m, target[1])));
        // A mixed state when the members differ.
        input.indeterminate = values.some(Boolean) && !values.every(Boolean);
        input.checked = values.every(Boolean);
      } else {
        input.checked = Boolean(rt.value(id, "value"));
      }
    };
    input.addEventListener("change", () => {
      if (!activeOf(rt, id)) {
        this.show();
        return;
      }
      // A click on a mixed toggle sets every member to true.
      const v = input.indeterminate ? true : input.checked;
      if (target) {
        scheduler.claim([`${target[0]}:${target[1] ?? ""}`], this);
        rt.write(target[0], target[1], v);
      } else {
        rt.write(id, "value", v);
      }
      this.show();
      const player = playerFor(rt, rt.objects[id]!);
      if (player) scheduler.start(player, this);
    });
    this.input = input;
    this.show();
    // The label follows what it is given, as anything bound does.
    const text = document.createTextNode(labelOf(rt, id));
    this.named = () => {
      text.data = labelOf(rt, id);
    };
    const label = document.createElement("label");
    label.append(input, text);
    this.replaceChildren(label);
  }

  protected update(): void {
    this.show();
    this.named();
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
  ["mtp-toggle", MtpToggle],
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
