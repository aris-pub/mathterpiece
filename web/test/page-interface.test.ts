// Each view's and control's page state, shown on it as data-mtp-… attributes, and the inputs a
// script acts through (docs/page-interface.md; the author, 2026-11-13).
import { beforeEach, describe, expect, it } from "vitest";
import type { Doc } from "../src/doc.ts";
import { type MtpModel, define, frames } from "../src/elements.ts";
import type { Runtime } from "../src/runtime.ts";
import { doc } from "./helpers.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};

function pass(seconds: number, step = 0.1): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

function page(body: string, file: Doc): [MtpModel, Runtime] {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = file;
  return [model, model.runtime!];
}

beforeEach(() => {
  queued = [];
  clock = 0;
});

const input = (el: Element, name: string) => el.querySelector(`[data-mtp-input="${name}"]`) as HTMLElement | null;

describe("a control's page state", () => {
  const all = `<mtp-button model="m" name="go"></mtp-button><mtp-slider model="m" name="sl"></mtp-slider><mtp-toggle model="m" name="t"></mtp-toggle>`;
  const el = (tag: string) => document.querySelector(tag) as HTMLElement;

  it("names each control's input: a button's button, a toggle's box and a slider's track", () => {
    page(all, doc("active"));
    expect(input(el("mtp-button"), "button")?.tagName).toBe("BUTTON");
    expect((input(el("mtp-toggle"), "box") as HTMLInputElement).type).toBe("checkbox");
    expect((input(el("mtp-slider"), "track") as HTMLInputElement).type).toBe("range");
  });

  it("marks a control inactive while its (active bool) does not hold, and fires mtp-state", () => {
    const [, rt] = page(all, doc("active"));
    let told = 0;
    for (const tag of ["mtp-button", "mtp-slider", "mtp-toggle"]) el(tag).addEventListener("mtp-state", () => told++);
    expect(["mtp-button", "mtp-slider", "mtp-toggle"].map((t) => el(t).hasAttribute("data-mtp-inactive"))).toEqual([false, false, false]);
    rt.write(rt.id("k"), null, 5);
    expect(["mtp-button", "mtp-slider", "mtp-toggle"].map((t) => el(t).hasAttribute("data-mtp-inactive"))).toEqual([true, true, true]);
    expect(told).toBe(3);
  });

  it("marks a slider held from the press to the release", () => {
    page(all, doc("active"));
    const track = input(el("mtp-slider"), "track")!;
    track.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    expect(el("mtp-slider").hasAttribute("data-mtp-held")).toBe(true);
    track.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
    expect(el("mtp-slider").hasAttribute("data-mtp-held")).toBe(false);
  });
});

describe("a view's page state", () => {
  it("shows its mode, quiet or live, and names its switch", () => {
    page(`<mtp-canvas model="m" name="left"></mtp-canvas>`, doc("quiet"));
    const view = document.querySelector("mtp-canvas") as HTMLElement;
    expect(view.getAttribute("data-mtp-mode")).toBe("quiet");
    let told = 0;
    view.addEventListener("mtp-state", () => told++);
    input(view, "switch")!.click();
    expect(view.getAttribute("data-mtp-mode")).toBe("live");
    expect(told).toBe(1);
  });
});

describe("the page interface", () => {
  it("has no mtp-mode or mtp-rest events, and no methods that change an element", () => {
    const [model] = page(`<mtp-canvas model="m" name="left"></mtp-canvas>`, doc("quiet"));
    const fired: string[] = [];
    for (const name of ["mtp-mode", "mtp-rest"]) document.addEventListener(name, () => fired.push(name));
    input(document.querySelector("mtp-canvas")!, "switch")!.click();
    pass(1.5);
    expect(fired).toEqual([]);
    expect("setLive" in model).toBe(false);
    expect("whenRest" in model).toBe(false);
  });
});
