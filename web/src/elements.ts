// The page elements: <mtp-model> holds a figure's JSON and its runtime, and views placed
// anywhere in the page find it by id, so an author can put each canvas where it fits.
import type { Doc } from "./doc.ts";
import { Runtime } from "./runtime.ts";
import { draw } from "./svg.ts";

export const FORMAT_VERSION = 1;
const READY = "mtp-ready";

export class MtpModel extends HTMLElement {
  runtime: Runtime | null = null;
  error: string | null = null;

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
    this.runtime = new Runtime(doc);
    this.error = null;
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }

  private fail(message: string): void {
    this.runtime = null;
    this.error = message;
    this.dispatchEvent(new Event(READY, { bubbles: true }));
  }
}

export class MtpCanvas extends HTMLElement {
  private svg: SVGSVGElement | null = null;
  private listener = (event: Event) => {
    if ((event.target as Element).id === this.getAttribute("model")) this.render();
  };

  connectedCallback(): void {
    document.addEventListener(READY, this.listener);
    const model = this.model();
    if (model && (model.runtime || model.error)) this.render();
  }

  disconnectedCallback(): void {
    document.removeEventListener(READY, this.listener);
  }

  private model(): MtpModel | null {
    const id = this.getAttribute("model");
    const el = id ? document.getElementById(id) : null;
    return el instanceof MtpModel ? el : null;
  }

  render(): void {
    const model = this.model();
    if (!model) return;
    try {
      if (model.error) throw new Error(model.error);
      const rt = model.runtime;
      if (!rt) return;
      const name = this.getAttribute("name");
      const canvas = rt.objects.find((o) => o.kind === "canvas" && (name === null || o.name === name));
      if (!canvas) throw new Error(name === null ? "the figure has no canvas" : `no canvas named ${name}`);
      this.svg = draw(rt, canvas.id, this.svg ?? undefined);
      if (this.svg.parentNode !== this) this.replaceChildren(this.svg);
    } catch (err) {
      this.svg = null;
      const message = document.createElement("pre");
      message.className = "mtp-error";
      message.textContent = (err as Error).message;
      this.replaceChildren(message);
    }
  }
}

/** Registers the elements; safe to call more than once. */
export function define(): void {
  if (!customElements.get("mtp-model")) customElements.define("mtp-model", MtpModel);
  if (!customElements.get("mtp-canvas")) customElements.define("mtp-canvas", MtpCanvas);
}
