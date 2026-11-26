// The jumpers (docs/spec/controls.md) with real layout and a real pointer, from .mtpc written by
// hand, since the compiler cannot write them yet.
import { describe, expect, it } from "vitest";
import { cdp } from "vitest/browser";
import type { Doc } from "../../src/doc.ts";
import { type MtpModel, define } from "../../src/elements.ts";

define();

const session = cdp();

const frames = (n = 2) =>
  new Promise<void>((r) => {
    const step = (k: number) => (k <= 0 ? r() : requestAnimationFrame(() => step(k - 1)));
    step(n);
  });

const free = (type: unknown, value: unknown) => ({ type, free: value });
const none = free({ union: ["real", "none"] }, null);
const variable = (name: string, type: unknown, value: unknown) => ({ kind: "variable", type, access: "scene", name, token: false, value: free(type, value) });
const control = (kind: string, keys: object) => ({ kind, type: { component: kind }, access: "page", name: "c", conditions: [], active: null, ...keys });

async function open(tag: string, v: object, c: object): Promise<MtpModel> {
  document.body.innerHTML = `<mtp-model id="m"></mtp-model><${tag} model="m" name="c"></${tag}>`;
  const model = document.querySelector("mtp-model") as MtpModel;
  model.doc = { mtpc: 1, types: [], objects: [v, c], functions: [], names: { [(v as { name: string }).name]: 0, c: 1 } } as unknown as Doc;
  await frames();
  return model;
}

const box = (el: Element) => el.getBoundingClientRect();
const center = (el: Element): [number, number] => {
  const b = box(el);
  return [b.left + b.width / 2, b.top + b.height / 2];
};

async function tap([x, y]: [number, number]): Promise<void> {
  for (const type of ["mousePressed", "mouseReleased"] as const)
    await session.send("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mousePressed" ? 1 : 0, clickCount: 1 });
  await frames();
}

describe("the jumpers in a browser", () => {
  it("a slider's thumb stands where its value is, and a press on the track writes the value there", async () => {
    const model = await open(
      "mtp-slider",
      variable("k", "real", 0.25),
      control("slider", { target: [0, null], attrs: { label: free("string", "k"), from: free("real", 0), to: free("real", 1), step: none, ticks: none } }),
    );
    const track = document.querySelector("mtp-slider .mtp-track")!;
    const thumb = document.querySelector("mtp-slider .mtp-thumb")!;
    const t = box(track);
    expect([box(thumb).width, box(thumb).height]).toEqual([16, 16]);
    expect(center(thumb)[0]).toBeCloseTo(t.left + 8 + 0.25 * (t.width - 16), 0);
    await tap([t.left + 8 + 0.75 * (t.width - 16), t.top + t.height / 2]);
    expect(model.runtime!.value(0, null) as number).toBeCloseTo(0.75, 1);
    expect(document.activeElement).toBe(thumb);
  });

  it("a dial's thumb sits on its ring, and a press on the ring writes the value there", async () => {
    const model = await open(
      "mtp-dial",
      variable("theta", { refine: "real", constraints: [["wrap", 0, 360]] }, 0),
      control("dial", { target: [0, null], attrs: { label: free("string", "theta"), step: free({ union: ["real", "none"] }, 15), ticks: none } }),
    );
    const svg = document.querySelector("mtp-dial svg")!;
    const thumb = document.querySelector("mtp-dial .mtp-thumb")!;
    const s = box(svg);
    const r = 0.4 * s.width;
    expect(center(thumb)[0]).toBeCloseTo(s.left + s.width / 2, 0);
    expect(center(thumb)[1]).toBeCloseTo(s.top + s.height / 2 - r, 0);
    await tap([s.left + s.width / 2 + r, s.top + s.height / 2]);
    expect(model.runtime!.value(0, null)).toBe(90);
    expect(center(thumb)[0]).toBeCloseTo(s.left + s.width / 2 + r, 0);
    expect(document.querySelectorAll("mtp-dial .mtp-tick").length).toBe(24);
  });

  it("a number field outlines its box in red after a refused commit, and underlines a value that can only be scrubbed", async () => {
    await open(
      "mtp-number-field",
      variable("n", "real", 5),
      control("number-field", { target: [0, null], attrs: { label: free("string", "n"), step: free("real", 1), buttons: free("bool", true), typing: free("bool", true) } }),
    );
    const field = document.querySelector("mtp-number-field .mtp-box")!;
    const before = getComputedStyle(field).borderTopColor;
    const input = document.querySelector("mtp-number-field input") as HTMLInputElement;
    input.focus();
    input.value = "many";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(field.classList.contains("mtp-refused")).toBe(true);
    // The outline comes in over a short transition.
    await new Promise((r) => setTimeout(r, 300));
    expect(getComputedStyle(field).borderTopColor).not.toBe(before);
    expect(box(document.querySelector("mtp-number-field .mtp-live")!).width).toBeLessThanOrEqual(1);

    await open(
      "mtp-number-field",
      variable("n", "real", 5),
      control("number-field", { target: [0, null], attrs: { label: free("string", "n"), step: free("real", 1), buttons: free("bool", false), typing: free("bool", false) } }),
    );
    const value = document.querySelector("mtp-number-field .mtp-value")!;
    expect(getComputedStyle(value).textDecorationStyle).toBe("dotted");
    expect(getComputedStyle(value).cursor).toBe("ew-resize");
  });

  it("a select's menu opens a list under its button, and a press on an option chooses it", async () => {
    const model = await open(
      "mtp-select",
      variable("w", "string", "a"),
      control("select", { target: [0, null], as: "menu", options: [{ value: free("string", "a") }, { value: free("string", "b") }], attrs: { label: free("string", "w") } }),
    );
    const button = document.querySelector("mtp-select .mtp-menu-button")!;
    await tap(center(button));
    const list = document.querySelector("mtp-select .mtp-listbox")!;
    expect(box(list).top).toBeGreaterThanOrEqual(box(button).bottom);
    await tap(center(document.querySelectorAll("mtp-select .mtp-option")[1]!));
    expect(model.runtime!.value(0, null)).toBe("b");
    expect(getComputedStyle(list).display).toBe("none");
  });
});
