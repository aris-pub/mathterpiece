// The page elements: <mtp-model> holds a figure's JSON and its runtime, and views and controls
// placed anywhere in the page find it by id, so an author can put each one where it fits.
import { Animator } from "./animate.ts";
import { fontCss, hex, parseComputed } from "./colors.ts";
import { Drags } from "./drag.ts";
import type { Doc, Obj } from "./doc.ts";
import { Runtime } from "./runtime.ts";
import { draw, viewOf } from "./svg.ts";

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
  animator: Animator | null = null;
  drags: Drags | null = null;
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
    this.animator = new Animator(rt, () => this.changed(), () => this.wake());
    this.drags = new Drags(rt);
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

  protected abstract setup(model: MtpModel, rt: Runtime, animator: Animator): void;
  protected abstract update(): void;
}

export class MtpCanvas extends MtpPart {
  private svg: SVGSVGElement | null = null;
  private redraw: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, animator: Animator): void {
    const name = this.getAttribute("name");
    const canvas = rt.objects.find((o) => o.kind === "canvas" && (name === null || o.name === name));
    if (!canvas) throw new Error(name === null ? "the figure has no canvas" : `no canvas named ${name}`);
    const drags = model.drags as Drags;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    this.svg = svg;
    this.redraw = () => {
      draw(rt, canvas.id, svg);
      markDraggable(svg, drags);
    };
    this.redraw();
    this.replaceChildren(svg);
    const toScene = (event: PointerEvent): [number, number] => scenePoint(rt, canvas.id, svg, event);
    svg.addEventListener("pointerdown", (event) => {
      const hit = (event.target as Element).closest?.("[data-mtp-id]");
      if (!hit || !drags.grab(Number(hit.getAttribute("data-mtp-id")), toScene(event))) return;
      animator.cancel();
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

// Shapes that a press would drag take the pointer, so touch screens drag them instead of scrolling.
function markDraggable(svg: SVGSVGElement, drags: Drags): void {
  for (const el of svg.querySelectorAll<SVGElement>("[data-mtp-id]")) {
    if (!drags.draggable(Number(el.getAttribute("data-mtp-id")))) continue;
    el.style.touchAction = "none";
    el.style.cursor = "grab";
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

export class MtpSlider extends MtpPart {
  private sync: () => void = () => {};

  protected setup(model: MtpModel, rt: Runtime, animator: Animator): void {
    const control = this.find(rt, "slider");
    const [target, attr] = control.target as [number, string];
    const whole = control.type === "int";
    const step = rt.value(control.id, "step");
    const input = document.createElement("input");
    input.type = "range";
    input.min = String(rt.value(control.id, "min"));
    input.max = String(rt.value(control.id, "max"));
    input.step = whole ? "1" : step === null ? "any" : String(step);
    input.value = String(rt.value(target, attr));
    input.addEventListener("input", () => {
      animator.cancel();
      const value = Number(input.value);
      rt.write(target, attr, whole ? Math.round(value) : value);
      model.changed();
    });
    const label = document.createElement("label");
    label.append(String(rt.value(control.id, "label")), " ", input);
    this.replaceChildren(label);
    this.sync = () => {
      input.value = String(rt.value(target, attr));
    };
  }

  protected update(): void {
    this.sync();
  }
}

export class MtpButton extends MtpPart {
  protected setup(_model: MtpModel, rt: Runtime, animator: Animator): void {
    const control = this.find(rt, "button");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(rt.value(control.id, "label"));
    button.addEventListener("click", () => {
      animator.cancel();
      animator.go(control.state as number, rt.value(control.id, "duration"), rt.value(control.id, "ease"));
    });
    this.replaceChildren(button);
  }

  protected update(): void {}
}

export class MtpSteps extends MtpPart {
  private sync: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, animator: Animator): void {
    const control = this.find(rt, "steps");
    const states = control.states ?? [];
    const buttons = states.map((state, k) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = rt.obj(state).name ?? String(k + 1);
      button.addEventListener("click", () => {
        animator.cancel();
        animator.go(state, rt.value(control.id, "duration"), rt.value(control.id, "ease"));
      });
      return button;
    });
    const group = document.createElement("div");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", String(rt.value(control.id, "label")));
    group.append(...buttons);
    this.replaceChildren(group);
    this.sync = () => {
      states.forEach((state, k) => buttons[k]?.setAttribute("aria-pressed", String(rt.holds(state))));
    };
    this.sync();
  }

  protected update(): void {
    this.sync();
  }
}

export class MtpPlay extends MtpPart {
  protected setup(_model: MtpModel, rt: Runtime, animator: Animator): void {
    const control = this.find(rt, "play");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(rt.value(control.id, "label"));
    button.addEventListener("click", () => animator.play(control.id));
    this.replaceChildren(button);
  }

  protected update(): void {}
}

const ELEMENTS: Record<string, CustomElementConstructor> = {
  "mtp-model": MtpModel,
  "mtp-canvas": MtpCanvas,
  "mtp-readout": MtpReadout,
  "mtp-slider": MtpSlider,
  "mtp-button": MtpButton,
  "mtp-steps": MtpSteps,
  "mtp-play": MtpPlay,
};

/** Registers the elements; safe to call more than once. */
export function define(): void {
  for (const [tag, element] of Object.entries(ELEMENTS)) {
    if (!customElements.get(tag)) customElements.define(tag, element);
  }
}
