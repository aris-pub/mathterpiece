// Recording mode (mtp-mvje.1): one figure on a 9:16 page, for recording a vertical short while a
// play runs. It shows one canvas and, under it, only the play's bars and the line naming the step:
// no button the viewer could not press, nothing else of the page, and no cursor. The presenter
// drives the play with its keys (reference.md, "A play's keys"), which work from anywhere on a
// page with one play.
import type { Doc } from "./doc.ts";

export interface Recording {
  canvas: string;
  play: string | null;
}

/** What a page's address asks to record: ?record, with &canvas=name and &play=name to choose; by
 * default the figure's first canvas and its first play. Null when it asks for none, or the figure
 * has no canvas of that name. */
export function recordingOf(search: string, doc: Doc): Recording | null {
  const params = new URLSearchParams(search);
  if (!params.has("record")) return null;
  const named = (kind: string, name: string | null) =>
    doc.objects.find((o) => o.kind === kind && o.name && (name === null || o.name === name))?.name ?? null;
  const canvas = named("canvas", params.get("canvas"));
  if (canvas === null) return null;
  return { canvas, play: named("play", params.get("play")) };
}

const STYLE = `
html.mtp-recording, html.mtp-recording body { margin: 0; height: 100%; overflow: hidden; }
html.mtp-recording body > :not(.mtp-record) { display: none !important; }
html.mtp-recording, html.mtp-recording * { cursor: none !important; }
.mtp-record {
  position: fixed; inset: 0; display: grid; place-items: center;
  background: color-mix(in srgb, var(--text-body, black) 14%, var(--surface-page, white));
}
.mtp-record-frame {
  box-sizing: border-box; aspect-ratio: 9 / 16; height: min(100vh, 100vw * 16 / 9);
  display: flex; flex-direction: column; justify-content: center; gap: 1.5rem;
  padding: 6% 6% 9%; overflow: hidden;
  background: var(--surface-page, white); color: var(--text-body, black);
}
.mtp-record-frame mtp-canvas { display: block; flex: none; width: 100%; margin: 0 auto; }
.mtp-record-frame mtp-canvas svg { display: block; width: 100%; height: auto; }
.mtp-record-frame mtp-play { min-width: 0; zoom: 1.25; }
.mtp-record-frame mtp-play .mtp-play-button { display: none; }
.mtp-record-frame mtp-play .mtp-now { font-size: 1rem; }
/* A viewer cannot press the switch of a view with a quiet mode, and the play shows whether its
   view is quiet or not. */
.mtp-record-frame .mtp-switch { display: none; }
html.mtp-recording .mtp-record-frame mtp-play[data-mtp-folded] { display: flex !important; }
`;

/** Shows the recording page for the model with the given id: the canvas and the play's
 * indicator in a 9:16 frame that fits the window, everything else on the page hidden. */
export function record(model: string, doc: Doc, rec: Recording): HTMLElement {
  if (!document.getElementById("mtp-record-style")) {
    const style = document.createElement("style");
    style.id = "mtp-record-style";
    style.textContent = STYLE;
    document.head.append(style);
  }
  document.documentElement.classList.add("mtp-recording");
  const stage = document.createElement("div");
  stage.className = "mtp-record";
  const frame = document.createElement("div");
  frame.className = "mtp-record-frame";
  const part = (kind: string, name: string) => {
    const el = document.createElement(`mtp-${kind}`);
    el.setAttribute("model", model);
    el.setAttribute("name", name);
    return el;
  };
  const canvas = part("canvas", rec.canvas);
  frame.append(canvas);
  if (rec.play !== null) frame.append(part("play", rec.play));
  stage.append(frame);
  document.body.append(stage);
  // The canvas takes the frame's width, unless its view box is too tall for the room left: then
  // it gives up width, as the dev page fits a figure to the window.
  const view = doc.objects.find((o) => o.kind === "canvas" && o.name === rec.canvas);
  const fit = () => {
    canvas.style.maxWidth = "";
    const box = canvas.querySelector("svg")?.viewBox?.baseVal;
    if (!view || !box || !box.width || !box.height) return;
    const inner = frame.clientHeight - parseFloat(getComputedStyle(frame).paddingTop) - parseFloat(getComputedStyle(frame).paddingBottom);
    const rest = frame.lastElementChild === canvas ? 0 : (frame.lastElementChild as HTMLElement).getBoundingClientRect().height + 24;
    const room = inner - rest;
    if (room > 0 && (canvas.clientWidth * box.height) / box.width > room) canvas.style.maxWidth = `${(room * box.width) / box.height}px`;
  };
  addEventListener("resize", fit);
  requestAnimationFrame(() => requestAnimationFrame(fit));
  return stage;
}
