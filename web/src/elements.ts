// The page elements: <mtp-model> holds a figure's JSON and its runtime, and views and controls
// placed anywhere in the page find it by id, so an author can put each one where it fits.
import { Scheduler } from "./animate.ts";
import { fontCss, hex, parseComputed } from "./colors.ts";
import { Clicks } from "./click.ts";
import { Drags } from "./drag.ts";
import type { Doc, Obj } from "./doc.ts";
import { Runtime } from "./runtime.ts";
import { Player, toSpec } from "./player.ts";
import { draw, shownNow, viewOf } from "./svg.ts";
import { type Ease, applyEase } from "./transitions.ts";

export const FORMAT_VERSION = 1;
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
  animator: Scheduler | null = null;
  drags: Drags | null = null;
  clicks: Clicks | null = null;
  error: string | null = null;
  private running = false;
  private last = 0;
  private watching = false;

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
    if (doc.mtp !== FORMAT_VERSION) {
      this.fail(`this runtime reads format version ${FORMAT_VERSION}, but the figure is version ${String(doc.mtp)}`);
      return;
    }
    const rt = new Runtime(doc, Math.random, (css, property) => this.resolve(css, property));
    this.runtime = rt;
    if (doc.objects.some((o) => o.kind === "color" || o.kind === "font")) this.watchStyles();
    this.animator = new Scheduler(rt, () => this.changed(), () => this.wake());
    this.drags = new Drags(rt);
    this.clicks = new Clicks(rt);
    this.error = null;
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }

  // What the page makes of a CSS value: CSS works it out on a hidden element inside this one, so
  // page rules on any ancestor (such as :root) apply. Colors come back as #rrggbbaa.
  private resolve(css: string, property: string): string | null {
    let probe = this.querySelector<HTMLElement>(":scope > .mtp-probe");
    if (!probe) {
      probe = document.createElement("span");
      probe.className = "mtp-probe";
      probe.hidden = true;
      this.append(probe);
    }
    probe.style.setProperty(property, css);
    const computed = getComputedStyle(probe).getPropertyValue(property);
    if (property !== "color") return computed || null;
    const color = parseComputed(computed);
    return color ? hex(color) : null;
  }

  // Browsers do not say when a CSS variable changes. Pages restyle by switching light and dark
  // mode, or by changing classes and styles on their root elements, so those are watched.
  private watchStyles(): void {
    if (this.watching) return;
    this.watching = true;
    const restyled = () => {
      this.runtime?.refresh();
      this.changed();
    };
    matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", restyled);
    const observer = new MutationObserver(restyled);
    for (const root of [document.documentElement, document.body]) {
      if (root) observer.observe(root, { attributes: true, attributeFilter: ["class", "style", "data-theme"] });
    }
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
    const animator = this.animator;
    if (!animator) return;
    animator.tick(Math.max(ms - this.last, 0) / 1000);
    this.last = ms;
    if (animator.busy()) frames.request((next) => this.frame(next));
    else this.running = false;
  }

  private fail(message: string): void {
    this.runtime = null;
    this.animator = null;
    this.drags = null;
    this.error = message;
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }
}

// What views and controls share: finding their model, and hearing when it loads or changes.
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
      if (model?.runtime && model.animator) this.setup(model, model.runtime, model.animator);
    });
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

  /** The named object of this element's kind. */
  protected find(rt: Runtime, kind: string): Obj {
    const name = this.getAttribute("name");
    const id = name === null ? undefined : rt.doc.names[name];
    const obj = id === undefined ? undefined : rt.obj(id);
    if (!obj) throw new Error(`no ${kind} named ${String(name)}`);
    if (obj.kind !== kind) throw new Error(`${String(name)} is a ${obj.kind}, not a ${kind}`);
    return obj;
  }

  protected abstract setup(model: MtpModel, rt: Runtime, animator: Scheduler): void;
  protected abstract update(): void;
}

export class MtpCanvas extends MtpPart {
  private svg: SVGSVGElement | null = null;
  private redraw: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, animator: Scheduler): void {
    const name = this.getAttribute("name");
    const canvas = rt.objects.find((o) => o.kind === "canvas" && (name === null || o.name === name));
    if (!canvas) throw new Error(name === null ? "the figure has no canvas" : `no canvas named ${name}`);
    const drags = model.drags as Drags;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    this.svg = svg;
    const fades = new Fades(rt, canvas.id, animator);
    const clicks = model.clicks as Clicks;
    this.redraw = () => {
      fades.follow();
      draw(rt, canvas.id, svg, (k) => fades.visible(k));
      markDraggable(svg, drags, clicks);
    };
    this.redraw();
    this.replaceChildren(svg);
    const toScene = (event: PointerEvent): [number, number] => scenePoint(rt, canvas.id, svg, event);
    // A click is a press and a release on the same object. Drawing replaces the elements, so
    // objects are compared by id.
    let pressed: number | null = null;
    const hitOf = (event: PointerEvent): number | null => {
      const direct = (event.target as Element).closest?.("[data-mtp-id]");
      const under = direct ?? document.elementFromPoint?.(event.clientX, event.clientY)?.closest("[data-mtp-id]");
      return under ? Number(under.getAttribute("data-mtp-id")) : null;
    };
    svg.addEventListener("pointerdown", (event) => {
      pressed = hitOf(event);
    });
    svg.addEventListener("pointerup", (event) => {
      const released = hitOf(event);
      const listener = pressed !== null && pressed === released ? clicks.find(pressed) : null;
      pressed = null;
      if (listener) animator.start(new Player(rt, listener.animation as number), listener);
    });
    svg.addEventListener("pointerdown", (event) => {
      const hit = (event.target as Element).closest?.("[data-mtp-id]");
      if (!hit || !drags.grab(Number(hit.getAttribute("data-mtp-id")), toScene(event))) return;
      animator.claim(drags.targets, drags);
      event.preventDefault();
      svg.setPointerCapture?.(event.pointerId);
    });
    svg.addEventListener("pointermove", (event) => {
      if (drags.dragging && drags.move(toScene(event))) model.changed();
    });
    const release = () => drags.release();
    svg.addEventListener("pointerup", release);
    svg.addEventListener("pointercancel", release);
  }

  protected update(): void {
    this.redraw();
  }
}

// How visible each thing a canvas lists is: the canvas's own state, which it moves along a
// transition when the thing's condition changes. Turning back midway takes the share of the
// duration that is left to cover, so it moves at the same speed.
class Fades {
  private level: number[];
  private wanted: boolean[];
  private moving = false;

  constructor(
    private rt: Runtime,
    private canvas: number,
    private animator: Scheduler,
  ) {
    const count = rt.obj(canvas).shows?.length ?? 0;
    this.wanted = Array.from({ length: count }, (_, k) => shownNow(rt, canvas, k));
    this.level = this.wanted.map((w) => (w ? 1 : 0));
  }

  visible(k: number): number {
    return this.level[k] ?? 0;
  }

  // Notices conditions that changed since the last drawing.
  follow(): void {
    const transitions = (this.rt.obj(this.canvas) as { transitions?: unknown[] }).transitions ?? [];
    this.wanted.forEach((was, k) => {
      const now = shownNow(this.rt, this.canvas, k);
      if (now === was) return;
      this.wanted[k] = now;
      if (!transitions[k]) this.level[k] = now ? 1 : 0;
    });
    const moving = this.wanted.some((w, k) => this.level[k] !== (w ? 1 : 0));
    if (moving && !this.moving) {
      this.moving = true;
      this.animator.addTicker((seconds) => this.step(seconds, transitions));
    }
  }

  private step(seconds: number, transitions: unknown[]): boolean {
    let more = false;
    this.wanted.forEach((w, k) => {
      const goal = w ? 1 : 0;
      const level = this.level[k] ?? 0;
      if (level === goal) return;
      const spec = toSpec(transitions[k], (e) => e);
      const duration = spec.kind === "single" ? (spec.duration ?? 0) : 0;
      const ease = spec.kind === "single" ? spec.ease : undefined;
      // Progress along the fade from hidden (0) to shown (1), eased, then back to a level.
      const progress = unease(level, ease) + (goal > level ? 1 : -1) * (duration > 0 ? seconds / duration : 1);
      const clamped = Math.min(Math.max(progress, 0), 1);
      this.level[k] = goal > level ? Math.min(easeOf(clamped, ease), 1) : Math.max(easeOf(clamped, ease), 0);
      if ((goal > level && clamped >= 1) || (goal < level && clamped <= 0)) this.level[k] = goal;
      if (this.level[k] !== goal) more = true;
    });
    this.moving = more;
    return more;
  }
}

function easeOf(p: number, ease: Ease | undefined): number {
  return applyEase(ease, p, () => p);
}

// The progress at which an ease reaches level, so a fade can carry on from where it is.
function unease(level: number, ease: Ease | undefined): number {
  let lo = 0;
  let hi = 1;
  for (let k = 0; k < 40; k++) {
    const mid = (lo + hi) / 2;
    if (easeOf(mid, ease) < level) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

// Shapes that a press would drag take the pointer, so touch screens drag them instead of scrolling.
function markDraggable(svg: SVGSVGElement, drags: Drags, clicks: Clicks): void {
  for (const el of svg.querySelectorAll<SVGElement>("[data-mtp-id]")) {
    const id = Number(el.getAttribute("data-mtp-id"));
    if (drags.draggable(id)) {
      el.style.touchAction = "none";
      el.style.cursor = "grab";
    } else if (clicks.find(id)) {
      el.style.cursor = "pointer";
    }
  }
}

// A pointer position in scene coordinates. The SVG keeps its view box's shape (centered, as with
// SVG's default preserveAspectRatio), so the scale is the smaller of the two.
function scenePoint(rt: Runtime, canvas: number, svg: SVGSVGElement, event: PointerEvent): [number, number] {
  const { box, toUser } = viewOf(rt, canvas);
  const [bx, by, bw, bh] = box;
  const rect = svg.getBoundingClientRect();
  const scale = Math.min(rect.width / bw, rect.height / bh);
  const ux = bx + (event.clientX - rect.left - (rect.width - bw * scale) / 2) / scale;
  const uy = by + (event.clientY - rect.top - (rect.height - bh * scale) / 2) / scale;
  return toUser.inverse().apply(ux, uy);
}

// A string from the scene, inline in the page's prose. Its font, if it has one, goes in a rule
// with the lowest priority, so it beats only inheritance: the page's own rules still win.
export class MtpReadout extends MtpPart {
  private sync: () => void = () => {};
  private rule: HTMLStyleElement | null = null;

  protected setup(model: MtpModel, rt: Runtime): void {
    const readout = this.find(rt, "readout");
    const selector = `:where(mtp-readout[model="${model.id}"][name="${readout.name}"])`;
    this.sync = () => {
      this.textContent = String(rt.value(readout.id, "value"));
      const declarations = readoutFont(rt, readout.id);
      if (!declarations && !this.rule) return;
      if (!this.rule) {
        this.rule = document.createElement("style");
        document.head.append(this.rule);
      }
      this.rule.textContent = declarations ? `${selector} { ${declarations} }` : "";
    };
    this.sync();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.rule?.remove();
    this.rule = null;
  }

  protected update(): void {
    this.sync();
  }
}

function readoutFont(rt: Runtime, id: number): string {
  return fontCss((attr) => rt.value(id, attr))
    .map(([property, css]) => `${property}: ${css};`)
    .join(" ");
}

// A transition scrubbed by hand: the knob's place on the track is the animation's progress. With
// one target, the knob follows the target when something else moves it.
export class MtpSlider extends MtpPart {
  private sync: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, animator: Scheduler): void {
    const control = this.find(rt, "slider");
    const player = new Player(rt, control.animation as number);
    const steps = rt.value(control.id, "step");
    const input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = "1";
    input.step = typeof steps === "number" ? String(1 / steps) : "any";
    const knob = player.knob();
    input.value = String(knob ?? 0);
    let holding = false;
    input.addEventListener("input", () => {
      if (!holding) {
        holding = true;
        player.release();
      }
      animator.claim(player.targets, this);
      player.scrub(Number(input.value));
      model.changed();
    });
    input.addEventListener("change", () => {
      holding = false;
    });
    const label = document.createElement("label");
    label.append(String(rt.value(control.id, "label")), " ", input);
    this.replaceChildren(label);
    this.sync = () => {
      if (holding) return;
      const place = player.knob();
      if (place !== null) input.value = String(place);
    };
  }

  protected update(): void {
    this.sync();
  }
}

// A labeled checkbox. Its value is a scene bool, or its own (outside the scene).
export class MtpToggle extends MtpPart {
  private sync: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, animator: Scheduler): void {
    const control = this.find(rt, "toggle");
    const [id, attr] = control.target ?? [control.id, "value"];
    const input = document.createElement("input");
    input.type = "checkbox";
    input.addEventListener("change", () => {
      if (control.target) animator.claim([`${id}.${attr}`], this);
      rt.write(id, attr, input.checked);
      model.changed();
    });
    const label = document.createElement("label");
    label.append(input, " ", String(rt.value(control.id, "label")));
    this.replaceChildren(label);
    this.sync = () => {
      input.checked = Boolean(rt.value(control.id, "value"));
    };
    this.sync();
  }

  protected update(): void {
    this.sync();
  }
}

// Sets off an animation when pressed.
export class MtpButton extends MtpPart {
  protected setup(_model: MtpModel, rt: Runtime, animator: Scheduler): void {
    const control = this.find(rt, "button");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(rt.value(control.id, "label"));
    button.addEventListener("click", () => animator.start(new Player(rt, control.animation as number), this));
    this.replaceChildren(button);
  }

  protected update(): void {}
}

// Plays and pauses an animation; with buttons, one more button per step of it. A step clicked
// while playing makes the tour jump there and go on; clicked while stopped, it runs that step
// alone, from wherever things are. A step's button is lit while the step holds.
export class MtpPlay extends MtpPart {
  private sync: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, animator: Scheduler): void {
    const control = this.find(rt, "play");
    const animation = control.animation as number;
    const label = String(rt.value(control.id, "label"));
    const play = document.createElement("button");
    play.type = "button";
    const tour = { kind: "tour" };
    const oneStep = { kind: "one step" };
    play.addEventListener("click", () => {
      const player = animator.playerOf(tour);
      if (animator.running(tour)) animator.pause(tour);
      else if (player && !player.done) animator.resume(tour);
      else animator.start(new Player(rt, animation), tour);
      this.sync();
    });
    const lights = new Player(rt, animation);
    const buttons = rt.value(control.id, "buttons")
      ? lights.steps.map((_, k) => {
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = stepLabel(rt, animation, k);
          button.addEventListener("click", () => {
            const player = animator.playerOf(tour);
            if (player && animator.running(tour)) {
              player.jump(k);
              animator.jumped(tour, player.steps[k]?.start ?? 0);
            } else {
              const single = new Player(rt, animation);
              single.only(k);
              animator.start(single, oneStep);
              animator.jumped(oneStep, single.steps[k]?.start ?? 0);
            }
          });
          return button;
        })
      : [];
    const group = document.createElement("div");
    group.setAttribute("role", "group");
    group.append(play, ...buttons);
    this.replaceChildren(group);
    this.sync = () => {
      play.textContent = animator.running(tour) ? "pause" : label;
      buttons.forEach((b, k) => b.setAttribute("aria-pressed", String(lights.holds(k))));
    };
    this.sync();
  }

  protected update(): void {
    this.sync();
  }
}

// A step's button says the name of the animation it plays, or its number.
function stepLabel(rt: Runtime, animation: number, k: number): string {
  const body = rt.obj(animation).body;
  const parts = Array.isArray(body) && body[0] === "in-order" ? (body.slice(2) as unknown[]) : [body];
  const step = parts.filter((p) => !(Array.isArray(p) && p[0] === "wait"))[k];
  if (Array.isArray(step) && step[0] === "animation") return rt.obj(step[1] as number).name ?? String(k + 1);
  return String(k + 1);
}

const ELEMENTS: Record<string, CustomElementConstructor> = {
  "mtp-model": MtpModel,
  "mtp-canvas": MtpCanvas,
  "mtp-readout": MtpReadout,
  "mtp-slider": MtpSlider,
  "mtp-toggle": MtpToggle,
  "mtp-button": MtpButton,
  "mtp-play": MtpPlay,
};

/** Registers the elements; safe to call more than once. */
export function define(): void {
  for (const [tag, element] of Object.entries(ELEMENTS)) {
    if (!customElements.get(tag)) customElements.define(tag, element);
  }
}
