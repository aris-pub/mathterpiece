// The inventory (mtp-4he1): what an author needs to put a world model's components on a page.
// It shows the lines that load the runtime and the compiled model, then every component in
// source order, each live with its name and the HTML that places it, then the listeners, which
// have no element, and the tokens, each with a control that restyles the components live.
import { dark, light } from "./builtins.ts";
import { cssVariable } from "./css.ts";
import type { Doc, Obj } from "./doc.ts";

const ELEMENTS = new Set(["canvas", "readout", "display", "slider", "toggle", "button", "play"]);
const LISTENERS = new Set([
  ...["on-drag", "on-click", "on-release", "on-dragstart", "on-dragend", "on-view"],
  ...["on-enter", "on-leave", "on-pointermove", "on-live", "on-quiet"],
]);

export interface InventoryOptions {
  /** The id of the <mtp-model> on this page that the live components read. */
  model: string;
  /** The id the HTML shown to the author gives the model, such as the source file's name. */
  id: string;
  /** The compiled model's file name, for the line that loads it from a file. */
  file: string;
}

/** Fills root with the inventory of the compiled model written as source, whose live components
 * read the model opts.model. It takes the text, not the parsed model, since the runtime changes
 * the model it loads, and the block an author copies must hold the file as written. */
export function inventory(root: HTMLElement, source: string, opts: InventoryOptions): void {
  const doc = JSON.parse(source) as Doc;
  const page = el("div", "mtp-inv");
  page.append(style());

  page.append(el("h2", "", "On a page"));
  page.append(el("p", "", "Load the runtime once on the page:"));
  page.append(snippet('<script type="module" src="mathterpiece.js"></script>'));
  page.append(el("p", "", `Then the compiled model, from the file ${opts.file} next to the page:`));
  page.append(snippet(`<mtp-model id="${opts.id}" src="${opts.file}"></mtp-model>`));
  page.append(el("p", "", "or from a block anywhere in the page, which needs no second file:"));
  const data = source.trim().replace(/<\//g, "<\\/");
  page.append(
    snippet(
      `<mtp-model id="${opts.id}" src="#${opts.id}-data"></mtp-model>\n` +
        `<script type="application/json" id="${opts.id}-data">{"mtpc":${doc.mtpc}, …}</script>`,
      `<mtp-model id="${opts.id}" src="#${opts.id}-data"></mtp-model>\n` +
        `<script type="application/json" id="${opts.id}-data">${data}</script>`,
    ),
  );

  page.append(el("h2", "", "Components"));
  page.append(el("p", "", "Each one, in the order the source declares it, with the line that places it."));
  const name = (id: number) => doc.objects[id]?.name ?? `#${id}`;
  for (const o of doc.objects) {
    if (ELEMENTS.has(o.kind) && o.name) page.append(component(o, opts));
    else if (LISTENERS.has(o.kind)) page.append(listener(doc, o, name));
  }

  const tokens = doc.objects.filter((o) => o.kind === "variable" && o.token && o.name);
  if (tokens.length) {
    page.append(el("h2", "", "Tokens"));
    page.append(
      el("p", "", "The page restyles these with CSS. The controls set each one on this page, so you can see what it changes."),
    );
    const table = el("table", "mtp-inv-tokens");
    for (const o of tokens) table.append(token(o));
    page.append(table);
  }
  root.replaceChildren(page);
}

function component(o: Obj, opts: InventoryOptions): HTMLElement {
  const entry = el("section", "mtp-inv-entry");
  entry.append(head(o.kind, o.name!));
  if (o.doc) entry.append(el("p", "mtp-inv-doc", o.doc));
  entry.append(snippet(`<mtp-${o.kind} model="${opts.id}" name="${o.name}"></mtp-${o.kind}>`));
  const live = document.createElement(`mtp-${o.kind}`);
  live.setAttribute("model", opts.model);
  live.setAttribute("name", o.name!);
  const holder = el("div", "mtp-inv-live");
  holder.append(live);
  entry.append(holder);
  return entry;
}

function listener(doc: Doc, o: Obj, name: (id: number) => string): HTMLElement {
  const entry = el("section", "mtp-inv-entry");
  const onView = o.kind === "on-live" || o.kind === "on-quiet";
  const onCanvas = o.kind === "on-view" || onView || (o.kind === "on-pointermove" && o.view != null);
  const of = onCanvas ? name(o.view!) : name(o.shape!);
  entry.append(head(o.kind, of));
  if (o.doc) entry.append(el("p", "mtp-inv-doc", o.doc));
  let what: string;
  if (o.kind === "on-drag") {
    what = `The reader drags ${of}, which moves ${target(o.target!, name)}.`;
  } else if (o.kind === "on-pointermove") {
    const over = onCanvas ? `the canvas ${of}` : of;
    what = `While the reader's pointer is over ${over}, it writes the pointer's position to ${target(o.target!, name)}.`;
  } else {
    const moves = movedBy(doc, o.animation ?? null).map((t) => target(t, name));
    const plays = moves.length ? `plays an animation that moves ${moves.join(", ")}` : "plays an animation";
    what = {
      "on-click": `When the reader clicks ${of}, it ${plays}.`,
      "on-release": `When the reader lets go of ${of}, it ${plays}.`,
      "on-dragstart": `When the reader starts dragging ${of}, it ${plays}.`,
      "on-dragend": `When the reader stops dragging ${of}, it ${plays}.`,
      "on-view": `When the canvas ${of} first comes into view, it ${plays}.`,
      "on-live": `When the reader makes ${of} live, with the hand in its corner, it ${plays}.`,
      "on-quiet": `When the reader puts ${of} back to quiet, with the cross in its corner, it ${plays}.`,
      "on-enter": `When the reader's pointer comes onto ${of}, it ${plays}.`,
      "on-leave": `When the reader's pointer leaves ${of}, it ${plays}.`,
    }[o.kind]!;
  }
  entry.append(el("p", "", what));
  entry.append(
    el(
      "p",
      "mtp-inv-note",
      onCanvas
        ? "It has no element of its own."
        : doc.objects[o.shape!]?.kind === "term"
          ? `It has no element of its own: it acts on ${of} in every display that shows its formula.`
          : `It has no element of its own: it acts on ${of} on every canvas that draws it.`,
    ),
  );
  return entry;
}

// A token's name, with its doc under it when it has one.
function tokenName(o: Obj): HTMLElement {
  const cell = el("td", "", o.name!);
  if (o.doc) cell.append(el("div", "mtp-inv-doc", o.doc));
  return cell;
}

function token(o: Obj): HTMLElement {
  const row = el("tr");
  const variable = cssVariable(o.name!);
  const value = (o.value && "free" in o.value ? o.value.free : null) as unknown;
  const root = document.documentElement.style;
  const control = el("td");
  const reset = el("button", "", "reset") as HTMLButtonElement;
  reset.type = "button";
  if (o.type === "color" && typeof value === "string") {
    // A color with a dark value of its own gets a control for each mode.
    const modes = value === light(value) ? [light(value)] : [light(value), dark(value)];
    const inputs = modes.map((start, k) => {
      const input = document.createElement("input");
      input.type = "color";
      input.value = start.slice(0, 7);
      input.setAttribute("aria-label", modes.length === 1 ? o.name! : `${o.name} ${k === 0 ? "light" : "dark"}`);
      return input;
    });
    const css = () => (inputs.length === 1 ? inputs[0]!.value : `light-dark(${inputs[0]!.value}, ${inputs[1]!.value})`);
    for (const input of inputs) input.addEventListener("input", () => root.setProperty(variable, css()));
    reset.addEventListener("click", () => {
      root.removeProperty(variable);
      inputs.forEach((input, k) => (input.value = modes[k]!.slice(0, 7)));
    });
    control.append(...inputs);
    row.append(tokenName(o), code(variable), control, code(value));
  } else if (o.type === "font" && value && typeof value === "object") {
    const font = value as Record<string, unknown>;
    const parts: [string, HTMLInputElement | HTMLSelectElement, string][] = [];
    const family = document.createElement("input");
    family.value = String(font.family ?? "");
    family.size = 28;
    const style = document.createElement("select");
    for (const s of ["normal", "italic"]) style.append(Object.assign(document.createElement("option"), { value: s, textContent: s }));
    style.value = String(font.style ?? "normal");
    const weight = document.createElement("input");
    weight.type = "number";
    weight.min = "100";
    weight.max = "900";
    weight.step = "100";
    weight.value = String(font.weight ?? 400);
    parts.push(["family", family, family.value], ["style", style, style.value], ["weight", weight, weight.value]);
    const names = el("div");
    for (const [part, input, start] of parts) {
      input.setAttribute("aria-label", `${o.name} ${part}`);
      input.addEventListener("input", () => root.setProperty(`${variable}-${part}`, input.value));
      reset.addEventListener("click", () => {
        root.removeProperty(`${variable}-${part}`);
        input.value = start;
      });
      control.append(input, " ");
      names.append(code(`${variable}-${part}`, "span"), document.createElement("br"));
    }
    const namesCell = el("td");
    namesCell.append(names);
    row.append(tokenName(o), namesCell, control, code(`${font.size ?? 16}px`));
  } else {
    row.append(tokenName(o), code(variable), el("td"), code(JSON.stringify(value)));
  }
  const last = el("td");
  last.append(reset);
  row.append(last);
  return row;
}

/** What an animation moves: every [id, attr] a move step names, in order. */
function movedBy(doc: Doc, animation: number | null): [number, string | null][] {
  if (animation === null) return [];
  const out: [number, string | null][] = [];
  const walk = (x: unknown): void => {
    if (!Array.isArray(x)) return;
    if (x[0] === "move" && Array.isArray(x[1])) out.push(x[1] as [number, string | null]);
    for (const y of x) walk(y);
  };
  walk(doc.objects[animation]?.steps);
  return out;
}

function target([id, attr]: [number, string | null], name: (id: number) => string): string {
  return attr ? `${name(id)}.${attr}` : name(id);
}

function head(kind: string, name: string): HTMLElement {
  const h = el("h3");
  h.append(el("span", "mtp-inv-kind", kind), " ", code(name, "span"));
  return h;
}

/** The text shown, with a button that copies it, or the fuller text given to copy. */
function snippet(shown: string, copied = shown): HTMLElement {
  const box = el("div", "mtp-inv-snippet");
  const pre = el("pre", "", shown);
  const button = el("button", "", "copy") as HTMLButtonElement;
  button.type = "button";
  button.addEventListener("click", () => {
    const done = () => {
      button.textContent = "copied";
      setTimeout(() => (button.textContent = "copy"), 1200);
    };
    navigator.clipboard?.writeText(copied).then(done, () => select(pre));
  });
  box.append(pre, button);
  return box;
}

function select(node: Node): void {
  const range = document.createRange();
  range.selectNodeContents(node);
  const selection = getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
}

function code(text: string, tag: "td" | "span" = "td"): HTMLElement {
  if (tag === "span") return el("code", "", text);
  const cell = el("td");
  cell.append(el("code", "", text));
  return cell;
}

function el(tag: string, cls = "", text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// Only the inventory's own layout: the components keep the runtime's look, and the page around
// it keeps its own.
function style(): HTMLStyleElement {
  const s = document.createElement("style");
  s.textContent = `
.mtp-inv { display: grid; gap: 0.9rem; }
.mtp-inv h2 { margin: 1.2rem 0 0; font-size: 1.15rem; }
.mtp-inv h3 { margin: 0; font-size: 1rem; font-weight: 600; }
.mtp-inv p { margin: 0; }
.mtp-inv-kind { font-weight: 400; opacity: 0.7; }
.mtp-inv-entry { display: grid; gap: 0.5rem; padding-top: 0.9rem; border-top: 1px solid rgb(128 128 128 / 0.25); }
.mtp-inv-note { opacity: 0.7; font-size: 0.9em; }
.mtp-inv-doc { font-style: italic; }
.mtp-inv-snippet { display: flex; gap: 0.5rem; align-items: flex-start; min-width: 0; }
.mtp-inv-snippet pre { flex: 1; min-width: 0; margin: 0; padding: 0.45rem 0.6rem; overflow-x: auto;
  font: 13px/1.45 ui-monospace, Menlo, Consolas, monospace; background: rgb(128 128 128 / 0.1); border-radius: 6px; }
.mtp-inv-live mtp-canvas { display: block; width: 100%; }
.mtp-inv-live mtp-canvas svg { display: block; width: 100%; height: auto; }
.mtp-inv-tokens { border-collapse: collapse; font-size: 14px; }
.mtp-inv-tokens td { padding: 0.35rem 0.8rem 0.35rem 0; border-bottom: 1px solid rgb(128 128 128 / 0.25); vertical-align: top; }
.mtp-inv code { font: 13px/1.45 ui-monospace, Menlo, Consolas, monospace; }
`;
  return s;
}
