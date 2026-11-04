// The page elements (docs/data-model.md, "On the page"): <mtp-model> holds a figure's .mtpc and
// its runtime, and views and controls placed anywhere in the page find it by id, so an author can
// put each one where it fits. Every writer emits writes to the model; views redraw on each change.
import { Scheduler } from "./animate.ts";
import { apply, invert } from "./builtins.ts";
import { Listeners } from "./click.ts";
import { type Doc, FORMAT_VERSION, type Obj, whenItems } from "./doc.ts";
import { Drags } from "./drag.ts";
import { Player } from "./player.ts";
import { Runtime } from "./runtime.ts";
import { type Look, draw, lookBox, viewOf, zoom } from "./svg.ts";
import { type Ease, applyEase } from "./transitions.ts";

export { FORMAT_VERSION };
const READY = "mtp-ready";
const CHANGE = "mtp-change";

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
  dragends: Listeners | null = null;
  error: string | null = null;
  // The views and controls that have come into view, and what waits for one to.
  private seen = new Set<number>();
  private waiting = new Map<number, (() => void)[]>();
  private running = false;
  private last = 0;

  connectedCallback(): void {
    const src = this.getAttribute("src");
    if (src && !this.runtime && !this.error) void this.load(src);
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

  connectedCallback(): void {
    document.addEventListener(READY, this.onReady);
    document.addEventListener(CHANGE, this.onChange);
    const model = this.model();
    if (model && (model.runtime || model.error)) this.build();
  }

  disconnectedCallback(): void {
    document.removeEventListener(READY, this.onReady);
    document.removeEventListener(CHANGE, this.onChange);
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
        this.setup(model, model.runtime, model.scheduler);
        this.watch(model);
      }
    });
  }

  // Tells the model when this element first comes into view (on-view, autoplay).
  private watch(model: MtpModel): void {
    const id = this.shown;
    if (id === null || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      observer.disconnect();
      model.markSeen(id);
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

function playerFor(rt: Runtime, writer: Obj): Player | null {
  return writer.animation === null || writer.animation === undefined
    ? null
    : new Player(rt, writer.animation, writer.conditions ?? []);
}

export class MtpCanvas extends MtpPart {
  private redraw: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const canvas = this.find(rt, "canvas");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    const drags = model.drags!;
    const clicks = model.clicks!;
    const releases = model.releases!;
    const dragends = model.dragends!;
    const toggles = new Toggles(rt, canvas, scheduler, () => this.redraw());
    const look: Look = { scale: 1, dx: 0, dy: 0 };
    this.redraw = () => {
      toggles.follow();
      draw(rt, canvas, svg, (k) => toggles.visible(k), look);
      for (const el of svg.querySelectorAll("[data-mtp-id]")) {
        const id = Number(el.getAttribute("data-mtp-id"));
        if (drags.draggable(id) || clicks.find(id)) (el as SVGElement).style.cursor = "pointer";
      }
    };
    this.replaceChildren(svg);
    this.redraw();
    // Font sizes are in screen pixels, so the drawing depends on the canvas's size on screen.
    let width = 0;
    new ResizeObserver(() => {
      const now = svg.getBoundingClientRect().width;
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
    // The pointer in the SVG's own coordinates, and in scene coordinates through the canvas's view.
    const toUser = (event: { clientX: number; clientY: number }): [number, number] => {
      const ctm = svg.getScreenCTM?.();
      const at: [number, number] = [event.clientX, event.clientY];
      if (!ctm) return at;
      return apply(invert([ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f]), at) as [number, number];
    };
    const toScene = (event: PointerEvent): [number, number] =>
      apply(invert(viewOf(rt, canvas).toUser), toUser(event)) as [number, number];
    const allows = (attr: "pan" | "zoom") => Boolean(rt.value(canvas, attr));
    if (allows("pan") || allows("zoom")) svg.style.touchAction = "none";
    // The reader zooms between the canvas's bounds and pans only inside its view box, so never
    // sees past what the author framed (the author, 2026-11-04).
    const inside = () => {
      const [, , w, h] = viewOf(rt, canvas).box as [number, number, number, number];
      const [mx, my] = [(w - w / look.scale) / 2, (h - h / look.scale) / 2];
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
    svg.addEventListener("pointerdown", (event) => {
      pressed = hitOf(event);
      if (pressed !== null && drags.grab(pressed, toScene(event))) {
        scheduler.claim(drags.targets, drags);
      } else if (allows("pan") || allows("zoom")) {
        touches.set(event.pointerId, [event.clientX, event.clientY]);
      } else {
        return;
      }
      event.preventDefault();
      svg.setPointerCapture?.(event.pointerId);
    });
    svg.addEventListener("pointermove", (event) => {
      if (drags.dragging) {
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
    svg.addEventListener("pointerup", (event) => {
      lift(event);
      // As JS's dragend, only a drag that moved ends.
      const ended = drags.moved ? drags.shape : null;
      drags.release();
      const released = hitOf(event);
      // pointerup comes before click, as in JS; the end of a drag comes between them.
      // As JS's click: on the nearest shape holding both the pressed and the released one,
      // whatever the pointer did between.
      const both = pressed !== null && released !== null ? holding(rt, pressed, released) : null;
      const click = both !== null ? clicks.find(both) : null;
      for (const listener of [
        released !== null ? releases.find(released) : null,
        ended !== null ? dragends.find(ended) : null,
        click,
      ]) {
        const player = listener ? playerFor(rt, listener) : null;
        if (listener && player) scheduler.start(player, listener);
      }
      pressed = null;
    });
    svg.addEventListener("pointercancel", (event) => {
      lift(event);
      drags.release();
    });
  }

  protected update(): void {
    this.redraw();
  }
}

// How visible each when item of a canvas is: the canvas's own state, which a toggle moves over the
// canvas's toggle-duration with its toggle-ease when the item's condition changes. Turning back midway covers only what is left, at the same
// speed.
class Toggles {
  private levels: number[];
  private wanted: boolean[];
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
    this.wanted = this.conditions();
    this.levels = this.wanted.map((w) => (w ? 1 : 0));
  }

  private conditions(): boolean[] {
    return whenItems(this.rt.objects[this.canvas]!).map(([cond]) => Boolean(this.rt.evaluate(cond)));
  }

  /** Starts moving toward what each condition says now. */
  follow(): void {
    const now = this.conditions();
    if (now.every((w, k) => w === this.wanted[k])) return;
    this.wanted = now;
    if (this.duration <= 0) {
      this.levels = now.map((w) => (w ? 1 : 0));
      return;
    }
    if (this.moving) return;
    this.moving = true;
    this.scheduler.addTicker((seconds) => {
      const step = seconds / this.duration;
      this.levels = this.levels.map((l, k) => (this.wanted[k] ? Math.min(l + step, 1) : Math.max(l - step, 0)));
      this.moving = this.levels.some((l, k) => l !== (this.wanted[k] ? 1 : 0));
      this.redraw();
      return this.moving;
    });
  }

  visible(k: number): number {
    return applyEase(this.ease, this.levels[k] ?? 0, (id) => this.rt.fn(id));
  }
}

export class MtpReadout extends MtpPart {
  private show: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime): void {
    const readout = this.find(rt, "readout");
    this.show = () => {
      this.textContent = String(rt.value(readout, "value"));
      const font = rt.objects[readout]!.attrs?.font ? (rt.value(readout, "font") as Record<string, unknown>) : null;
      for (const part of ["family", "style", "weight"]) {
        if (font?.[part] !== null && font?.[part] !== undefined) this.style.setProperty(`font-${part}`, String(font[part]));
      }
    };
    this.show();
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
    input.addEventListener("input", () => {
      if (!activeOf(rt, id)) return;
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
      for (let n = 0; n <= max; n++) {
        const d = distance(player.valueAt(n / max), now);
        if (d < gap) [best, gap] = [n, d];
      }
      input.value = String(best);
      rt.write(id, "position", best / max);
    };
    this.follow();
    this.gate = () => {
      input.disabled = !activeOf(rt, id);
    };
    this.gate();
    const label = document.createElement("label");
    label.textContent = labelOf(rt, id);
    label.append(input);
    this.replaceChildren(label);
  }

  protected update(): void {
    this.follow();
    this.gate();
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
    this.gate = () => {
      button.disabled = !activeOf(rt, id);
    };
    this.gate();
    this.replaceChildren(button);
  }

  protected update(): void {
    this.gate();
  }
}

export class MtpPlay extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "play");
    const play = document.createElement("button");
    let player: Player | null = null;
    play.addEventListener("click", () => {
      if (!activeOf(rt, id)) return;
      if (scheduler.running(this)) scheduler.pause(this);
      else if (player && !player.done && scheduler.playerOf(this)) scheduler.resume(this);
      else {
        player = playerFor(rt, rt.objects[id]!);
        if (player) scheduler.start(player, this);
      }
      this.refresh();
    });
    const steps: HTMLButtonElement[] = [];
    // A step clicked runs on its own, apart from the play: the play stops, and the step
    // animates from wherever things are. Starting it claims everything the play moves, not only
    // what the step moves, so it cancels the play and every other writer moving any of it.
    const alone = {};
    let single: { player: Player; k: number } | null = null;
    if (rt.value(id, "buttons")) {
      const spans = playerFor(rt, rt.objects[id]!)?.spans ?? [];
      spans.forEach((span, k) => {
        const b = document.createElement("button");
        b.textContent = String(k + 1);
        b.addEventListener("click", () => {
          if (!activeOf(rt, id)) return;
          const one = playerFor(rt, rt.objects[id]!);
          if (!one) return;
          one.only(k);
          single = { player: one, k };
          scheduler.start(one, alone, span.start);
          this.refresh();
        });
        steps.push(b);
      });
    }
    this.refresh = () => {
      const running = scheduler.running(this);
      play.textContent = running ? "pause" : labelOf(rt, id);
      const now = running
        ? (player?.stepNow() ?? null)
        : // The last frame of the step redraws before the scheduler drops it, so a step that is
          // done counts as over.
          single && scheduler.running(alone) && !single.player.done
          ? single.k
          : null;
      steps.forEach((b, k) => b.classList.toggle("mtp-lit", now === k));
      const active = activeOf(rt, id);
      for (const b of [play, ...steps]) b.disabled = !active;
      if (rt.value(id, "playing") !== running) rt.write(id, "playing", running);
      if (now !== null && rt.value(id, "step") !== now) rt.write(id, "step", now);
    };
    this.refresh();
    this.replaceChildren(play, ...steps);
    // (autoplay) starts it when the page loads; (autoplay x) the first time x comes into view.
    const start = () => {
      if (!activeOf(rt, id) || scheduler.running(this)) return;
      player = playerFor(rt, rt.objects[id]!);
      if (player) scheduler.start(player, this);
      this.refresh();
    };
    const auto = rt.objects[id]!.autoplay;
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
    });
    this.input = input;
    this.show();
    const label = document.createElement("label");
    label.append(input, labelOf(rt, id));
    this.replaceChildren(label);
  }

  protected update(): void {
    this.show();
  }
}

const ELEMENTS: [string, CustomElementConstructor][] = [
  ["mtp-model", MtpModel],
  ["mtp-canvas", MtpCanvas],
  ["mtp-readout", MtpReadout],
  ["mtp-slider", MtpSlider],
  ["mtp-button", MtpButton],
  ["mtp-play", MtpPlay],
  ["mtp-toggle", MtpToggle],
];

export function define(): void {
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
