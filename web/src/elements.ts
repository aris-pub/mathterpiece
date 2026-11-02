// The page elements (docs/data-model.md, "On the page"): <mtp-model> holds a figure's .mtpc and
// its runtime, and views and controls placed anywhere in the page find it by id, so an author can
// put each one where it fits. Every writer emits writes to the model; views redraw on each change.
import { Scheduler } from "./animate.ts";
import { apply, invert } from "./builtins.ts";
import { Clicks } from "./click.ts";
import { type Doc, FORMAT_VERSION, type Obj } from "./doc.ts";
import { Drags } from "./drag.ts";
import { Player } from "./player.ts";
import { Runtime } from "./runtime.ts";
import { draw, viewOf } from "./svg.ts";

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
  clicks: Clicks | null = null;
  error: string | null = null;
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
    this.clicks = new Clicks(rt);
    this.error = null;
    rt.onChange(() => this.changed());
    this.dispatchEvent(new Event(READY, { bubbles: true }));
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
      if (model?.runtime && model.scheduler) this.setup(model, model.runtime, model.scheduler);
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

  /** The id of the object this element shows, by its name attribute and kind. */
  protected find(rt: Runtime, kind: string): number {
    const name = this.getAttribute("name");
    const id = name === null ? undefined : rt.doc.names[name];
    const obj = id === undefined ? undefined : rt.objects[id];
    if (!obj) throw new Error(`no ${kind} named ${String(name)}`);
    if (obj.kind !== kind) throw new Error(`${String(name)} is a ${obj.kind}, not a ${kind}`);
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
    this.redraw = () => {
      draw(rt, canvas, svg);
      for (const el of svg.querySelectorAll("[data-mtp-id]")) {
        const id = Number(el.getAttribute("data-mtp-id"));
        if (drags.draggable(id) || clicks.find(id)) (el as SVGElement).style.cursor = "pointer";
      }
    };
    this.redraw();
    this.replaceChildren(svg);
    const hitOf = (event: PointerEvent): number | null => {
      const under = (event.target as Element).closest?.("[data-mtp-id]");
      return under ? Number(under.getAttribute("data-mtp-id")) : null;
    };
    // The pointer in scene coordinates: through the SVG's own coordinates, then the canvas's view.
    const toScene = (event: PointerEvent): [number, number] => {
      const ctm = svg.getScreenCTM?.();
      let user: [number, number] = [event.clientX, event.clientY];
      if (ctm) {
        const m = [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f];
        user = apply(invert(m), user) as [number, number];
      }
      return apply(invert(viewOf(rt, canvas).toUser), user) as [number, number];
    };
    // A click is a press and a release on the same shape; drawing replaces the elements, so
    // shapes are compared by id.
    let pressed: number | null = null;
    svg.addEventListener("pointerdown", (event) => {
      pressed = hitOf(event);
      if (pressed === null || !drags.grab(pressed, toScene(event))) return;
      scheduler.claim(drags.targets, drags);
      event.preventDefault();
      svg.setPointerCapture?.(event.pointerId);
    });
    svg.addEventListener("pointermove", (event) => {
      if (drags.dragging) drags.move(toScene(event));
    });
    svg.addEventListener("pointerup", (event) => {
      drags.release();
      const released = hitOf(event);
      const listener = pressed !== null && pressed === released ? clicks.find(pressed) : null;
      pressed = null;
      const player = listener ? playerFor(rt, listener) : null;
      if (listener && player) scheduler.start(player, listener);
    });
    svg.addEventListener("pointercancel", () => drags.release());
  }

  protected update(): void {
    this.redraw();
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

export class MtpSlider extends MtpPart {
  private input: HTMLInputElement | null = null;

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "slider");
    const player = playerFor(rt, rt.objects[id]!);
    const input = document.createElement("input");
    input.type = "range";
    const places = rt.objects[id]!.attrs?.step ? (rt.value(id, "step") as number) : null;
    // With (step n) the knob stops at n evenly spaced places.
    input.min = "0";
    input.max = places === null ? "1000" : String(places - 1);
    input.step = "1";
    input.value = String(Math.round((rt.value(id, "position") as number) * Number(input.max)));
    input.addEventListener("input", () => {
      const u = Number(input.value) / Number(input.max);
      if (player) {
        scheduler.claim(player.targets, this);
        player.scrub(u);
      }
      rt.write(id, "position", u);
    });
    input.addEventListener("change", () => player?.release());
    this.input = input;
    const label = document.createElement("label");
    label.textContent = labelOf(rt, id);
    label.append(input);
    this.replaceChildren(label);
  }

  protected update(): void {}
}

export class MtpButton extends MtpPart {
  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "button");
    const button = document.createElement("button");
    button.textContent = labelOf(rt, id);
    // A press plays the animation from the start; a press while it runs starts it again.
    button.addEventListener("click", () => {
      const player = playerFor(rt, rt.objects[id]!);
      if (player) scheduler.start(player, this);
    });
    this.replaceChildren(button);
  }

  protected update(): void {}
}

export class MtpPlay extends MtpPart {
  private refresh: () => void = () => {};

  protected setup(_model: MtpModel, rt: Runtime, scheduler: Scheduler): void {
    const id = this.find(rt, "play");
    const play = document.createElement("button");
    let player: Player | null = null;
    play.addEventListener("click", () => {
      if (scheduler.running(this)) scheduler.pause(this);
      else if (player && !player.done && scheduler.playerOf(this)) scheduler.resume(this);
      else {
        player = playerFor(rt, rt.objects[id]!);
        if (player) scheduler.start(player, this);
      }
      this.refresh();
    });
    const steps: HTMLButtonElement[] = [];
    if (rt.value(id, "buttons")) {
      const spans = playerFor(rt, rt.objects[id]!)?.spans ?? [];
      spans.forEach((span, k) => {
        const b = document.createElement("button");
        b.textContent = String(k + 1);
        // A step clicked while playing jumps there and carries on; while stopped, it runs from
        // there, from wherever things are.
        b.addEventListener("click", () => {
          player = playerFor(rt, rt.objects[id]!);
          if (player) scheduler.start(player, this, span.start);
          this.refresh();
        });
        steps.push(b);
      });
    }
    this.refresh = () => {
      const running = scheduler.running(this);
      play.textContent = running ? "pause" : labelOf(rt, id);
      const now = player?.stepNow() ?? null;
      steps.forEach((b, k) => b.classList.toggle("mtp-lit", running && now === k));
      if (rt.value(id, "playing") !== running) rt.write(id, "playing", running);
      if (now !== null && rt.value(id, "step") !== now) rt.write(id, "step", now);
    };
    this.refresh();
    this.replaceChildren(play, ...steps);
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
