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

// Tokens that BRAIID would set, so that the colors that a control is drawn in can be told apart.
const ACTIVE = "rgb(0, 0, 200)";
const SUBTLE = "rgb(100, 100, 100)";
const HILITE = "rgb(186, 227, 253)";
function tokens(): void {
  const root = document.documentElement.style;
  root.setProperty("--mtp-control-rest", ACTIVE);
  root.setProperty("--mtp-control-active", ACTIVE);
  root.setProperty("--text-subtle", SUBTLE);
  root.setProperty("--primary-200", HILITE);
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

  it("a menu with nothing chosen shows its label in its button, in a quieter color than a chosen option's", async () => {
    tokens();
    await open(
      "mtp-select",
      variable("w", "string", "z"),
      control("select", { target: [0, null], as: "menu", options: [{ value: free("string", "a") }, { value: free("string", "b") }], attrs: { label: free("string", "w") } }),
    );
    expect(getComputedStyle(document.querySelector("mtp-select .mtp-placeholder")!).color).toBe(SUBTLE);
    expect(getComputedStyle(document.querySelector("mtp-select .mtp-menu-text")!).color).toBe(ACTIVE);
  });

  it("a toggle's checkbox is drawn by the runtime, with the native checkbox unseen in the page", async () => {
    tokens();
    const model = await open(
      "mtp-toggle",
      variable("b", "bool", false),
      control("toggle", {
        target: [0, null],
        animation: null,
        attrs: { label: free("string", "show"), value: { type: "bool", bound: ["read", "bool", 0, null, null], deps: [[0, null]] } },
      }),
    );
    const input = document.querySelector("mtp-toggle input") as HTMLInputElement;
    const label = document.querySelector("mtp-toggle label")!;
    expect(input.type).toBe("checkbox");
    expect(getComputedStyle(input).opacity).toBe("0");
    const drawn = () => getComputedStyle(label, "::before");
    const mark = () => getComputedStyle(label, "::after");
    expect([drawn().width, drawn().height]).toEqual(["16px", "16px"]);
    expect(drawn().backgroundColor).not.toBe(HILITE);
    expect(mark().content).toBe("none");
    // A press on the drawn box reaches the native checkbox through its label.
    const b = box(label);
    await tap([b.left + 8, b.top + b.height / 2]);
    expect(model.runtime!.value(0, null)).toBe(true);
    expect(input.checked).toBe(true);
    expect(drawn().backgroundColor).toBe(HILITE);
    expect(drawn().borderTopColor).toBe(ACTIVE);
    expect(mark().content).not.toBe("none");
    expect(mark().borderRightColor).toBe(ACTIVE);
    // The mixed state, of a toggle whose group's members differ, is a bar.
    input.checked = false;
    input.indeterminate = true;
    expect(drawn().backgroundColor).toBe(HILITE);
    expect([mark().width, mark().height, mark().backgroundColor]).toEqual(["8px", "2px", ACTIVE]);
  });

  it("a drawn checkbox shows a focus ring when the native checkbox has the focus from the keyboard", async () => {
    tokens();
    await open(
      "mtp-multi-select",
      variable("l", { list: "string" }, []),
      control("multi-select", { target: [0, null], as: "checkbox", options: [{ value: free("string", "a") }], attrs: { label: free("string", "l") } }),
    );
    const line = document.querySelector("mtp-multi-select .mtp-mark")!;
    expect(getComputedStyle(line, "::before").outlineStyle).toBe("none");
    // A key pressed before the focus moves makes the browser count the focus as from the keyboard.
    await session.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Shift", code: "ShiftLeft", windowsVirtualKeyCode: 16 });
    await session.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Shift", code: "ShiftLeft", windowsVirtualKeyCode: 16 });
    (line.querySelector("input") as HTMLInputElement).focus();
    expect(getComputedStyle(line, "::before").outlineStyle).toBe("solid");
    expect(getComputedStyle(line, "::before").outlineWidth).toBe("2px");
  });

  it("a select's radio buttons are drawn by the runtime as round marks", async () => {
    tokens();
    const model = await open(
      "mtp-select",
      variable("w", "string", "a"),
      control("select", { target: [0, null], as: "radio", options: [{ value: free("string", "a") }, { value: free("string", "b") }], attrs: { label: free("string", "w") } }),
    );
    const [first, second] = [...document.querySelectorAll("mtp-select .mtp-mark")];
    expect(getComputedStyle(first!.querySelector("input")!).opacity).toBe("0");
    expect(getComputedStyle(first!, "::before").borderTopLeftRadius).toBe("50%");
    expect(getComputedStyle(first!, "::before").backgroundColor).toBe(HILITE);
    expect(getComputedStyle(first!, "::after").backgroundColor).toBe(ACTIVE);
    expect(getComputedStyle(first!, "::after").borderTopLeftRadius).toBe("50%");
    expect(getComputedStyle(second!, "::after").content).toBe("none");
    const b = box(second!);
    await tap([b.left + 8, b.top + b.height / 2]);
    expect(model.runtime!.value(0, null)).toBe("b");
    expect(getComputedStyle(second!, "::before").borderTopColor).toBe(ACTIVE);
  });
});
