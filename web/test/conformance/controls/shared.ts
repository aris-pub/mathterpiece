// What the conformance tests of docs/spec/controls.md share. The compiler cannot write the new
// controls yet, so each test holds its .mtpc, written by hand in the form that docs/mtpc.md gives.
import type { Attribute, Doc, Obj, Type } from "../../../src/doc.ts";
import { type MtpModel, define, frames } from "../../../src/elements.ts";
import { schemaProblem } from "../../../src/schema.ts";

define();

let queued: ((ms: number) => void)[] = [];
let clock = 0;
frames.request = (callback) => {
  queued.push(callback);
};
frames.now = () => clock;

/** Moves the page's clock on, frame by frame. */
export function pass(seconds: number, step = 0.05): void {
  for (let t = 0; t < seconds - 1e-9; t += step) {
    clock += step * 1000;
    const now = queued;
    queued = [];
    for (const f of now) f(clock);
  }
}

/** A free value. */
export const free = (type: Type, value: unknown): Attribute => ({ type, free: value });
export const str = (value: string): Attribute => free("string", value);
export const num = (value: number): Attribute => free("real", value);
export const bool = (value: boolean): Attribute => free("bool", value);
export const none = (): Attribute => free({ union: ["real", "none"] }, null);
export const maybe = (value: number): Attribute => free({ union: ["real", "none"] }, value);

/** A variable of the scene. */
export function variable(name: string, type: Type, value: unknown): Obj {
  return { kind: "variable", type, access: "scene", name, token: false, value: free(type, value) } as Obj;
}

/** A .mtpc of the given objects, each named object in names by its position. */
export function mtpc(...objects: object[]): Doc {
  const names: Record<string, number> = {};
  objects.forEach((o, i) => {
    const name = (o as { name?: string | null }).name;
    if (name) names[name] = i;
  });
  return { mtpc: 1, types: [], objects: objects as Obj[], functions: [], names };
}

/** A page with one model and the given elements, loaded from a .mtpc that must match the schema. */
export function page(body: string, doc: Doc): MtpModel {
  const problem = schemaProblem(structuredClone(doc));
  if (problem) throw new Error(problem);
  queued = [];
  document.body.innerHTML = `<mtp-model id="m"></mtp-model>${body}`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = doc;
  return model;
}

/** The value of a variable of the model by name. */
export function valueOf(model: MtpModel, name: string): unknown {
  const rt = model.runtime!;
  return rt.value(rt.id(name), null);
}

/** The input of a control by its data-mtp-input name. */
export function input(control: string, name: string): HTMLElement {
  const el = document.querySelector(`${control} [data-mtp-input="${name}"]`);
  if (!(el instanceof HTMLElement || el instanceof SVGElement)) throw new Error(`${control} has no input ${name}`);
  return el as HTMLElement;
}

export function hasInput(control: string, name: string): boolean {
  return document.querySelector(`${control} [data-mtp-input="${name}"]`) !== null;
}

/** Gives an element a box on the page, which happy-dom does not lay out. */
export function place(el: Element, left: number, top: number, width: number, height: number): void {
  el.getBoundingClientRect = () =>
    ({ left, top, width, height, right: left + width, bottom: top + height, x: left, y: top, toJSON: () => ({}) }) as DOMRect;
}

export function pointer(el: Element, type: string, x: number, y = 0, init: PointerEventInit = {}): void {
  el.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, pointerId: 1, button: 0, ...init }));
}

/** A press at one point and its release there. */
export function press(el: Element, x: number, y = 0, init: PointerEventInit = {}): void {
  pointer(el, "pointerdown", x, y, init);
  pointer(window as unknown as Element, "pointerup", x, y, init);
}

export function key(el: Element, k: string, init: KeyboardEventInit = {}): void {
  el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true, ...init }));
}

/** Types text into a box, as the reader does, without committing it. */
export function typeInto(box: HTMLInputElement, text: string): void {
  box.focus();
  box.value = text;
  box.dispatchEvent(new Event("input", { bubbles: true }));
}

/** A control object of a new kind, with the keys that every control has. */
export function control(kind: string, name: string, keys: Record<string, unknown>): object {
  return { kind, type: { component: kind }, access: "page", name, conditions: [], active: null, ...keys };
}

/** A writer's guard: before a write to the target, the value is clamped to the limit. */
export function guard(target: [number, string | null], op: ">=" | ">" | "<=" | "<", limit: number): object {
  return { target, op, limit: num(limit) };
}

export const REAL_0_1: Type = { refine: "real", constraints: [[">=", 0], ["<=", 1]] };
export const ANGLE: Type = { refine: "real", constraints: [["wrap", 0, 360]] };
export const HOUR: Type = { refine: "int", constraints: [["wrap", 0, 12]] };
